import numpy as np
from abc import ABC, abstractmethod
from os import cpu_count
from tqdm import tqdm
from xarray import Dataset

from foxes.core import MData, FData, TData
from foxes.utils import all_subclasses
import foxes.constants as FC

__global_engine_data__ = dict(
    engine=None,
)

class Engine(ABC):
    """
    Abstract base clas for foxes calculation engines
    
    Attributes
    ----------
    chunk_size_states: int
        The size of a states chunk
    chunk_size_points: int
        The size of a points chunk
    verbosity: int
        The verbosity level, 0 = silent
            
    :group: core
    
    """
    def __init__(
        self, 
        chunk_size_states=None, 
        chunk_size_points=None, 
        verbosity=1,
    ):
        """
        Constructor.
        
        Parameters
        ----------
        chunk_size_states: int, optional
            The size of a states chunk
        chunk_size_points: int, optional
            The size of a points chunk
        verbosity: int
            The verbosity level, 0 = silent
        
        """
        self.chunk_size_states = chunk_size_states
        self.chunk_size_points = chunk_size_points
        self.verbosity = verbosity
        self.__initialized = False
    
    def __repr__(self):
        s = f"chunk_size_states={self.chunk_size_states}, chunk_size_points={self.chunk_size_points}"
        return f"{type(self).__name__}({s})"
    
    @property
    def initialized(self):
        """
        Initialization flag.

        Returns
        -------
        ini: bool
            True if the model has been initialized.

        """
        return self.__initialized
    
    def initialize(self):
        """
        Initializes the engine.
        """
        if not self.initialized:
            if get_engine(error=False, default=False) is not None:
                raise ValueError(f"Cannot initialize engine '{type(self).__name__}', since engine already set to '{type(get_engine()).__name__}'")
            global __global_engine_data__
            __global_engine_data__["engine"] = self
            self.__initialized = True
        
    def finalize(self):
        """
        Finalizes the engine.
        """
        if self.initialized:
            global __global_engine_data__
            __global_engine_data__["engine"] = None
            self.__initialized = False
        
    def __enter__(self):
        if not self.initialized:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.initialized:
            self.finalize()
    
    def print(self, *args, level=1, **kwargs):
        """ Prints based on verbosity """
        if self.verbosity >= level:
            print(*args, **kwargs)
    
    @property
    def loop_dims(self):
        """
        Gets the loop dimensions (possibly chunked)
        
        Returns
        -------
        dims: list of str
            The loop dimensions (possibly chunked)
        
        """
        if self.chunk_size_states is None and self.chunk_size_states is None:
            return []
        elif self.chunk_size_states is None:
            return [FC.TARGET]
        elif self.chunk_size_points is None:
            return [FC.STATE]
        else:
            return [FC.STATE, FC.TARGET]

    def select_subsets(self, *datasets, sel=None, isel=None):
        """
        Takes subsets of datasets
        
        Parameters
        ----------
        datasets: tuple
            The xarray.Dataset or xarray.Dataarray objects
        sel: dict, optional
            The selection dictionary
        isel: dict, optional
            The index selection dictionary
        
        Returns
        -------
        subsets: list
            The subsets of the input data
        
        """

        if sel is not None:
            new_datasets = []
            for data in datasets:
                if data is not None:
                    s = {c: u for c, u in sel.items() if c in data.coords}
                    new_datasets.append(data.sel(s) if len(s) else data)
                else:
                    new_datasets.append(data)
            datasets = new_datasets

        if isel is not None:
            new_datasets = []
            for data in datasets:
                if data is not None:
                    s = {c: u for c, u in isel.items() if c in data.coords}
                    new_datasets.append(data.isel(s) if len(s) else data)
                else:
                    new_datasets.append(data)
            datasets = new_datasets
        
        return datasets

    def calc_chunk_sizes(self, n_states, n_targets=1):
        """
        Computes the sizes of states and points chunks
        
        Parameters
        ----------
        n_states: int
            The number of states
        n_targets: int
            The number of point targets
            
        Returns
        -------
        n_procs: int
            The number of processes to be used
        chunk_sizes_states: numpy.ndarray
            The sizes of all states chunks, shape: (n_chunks_states,)
        chunk_sizes_targets: numpy.ndarray
            The sizes of all targets chunks, shape: (n_chunks_targets,)
            
        """
        # determine states chunks:    
        n_chunks_states = 1
        chunk_sizes_states = [n_states]
        n_procs = cpu_count() if self.n_procs is None else self.n_procs
        if self.chunk_size_states is None: 
            chunk_size_states = max(int(n_states/n_procs), 1)
        else: 
            chunk_size_states = min(n_states, self.chunk_size_states)
        n_chunks_states = int(n_states/chunk_size_states)
        chunk_size_states = int(n_states/n_chunks_states)
        chunk_sizes_states = np.full(n_chunks_states, chunk_size_states, dtype=np.int32)
        extra = n_states - n_chunks_states*chunk_size_states
        if extra > 0:
            chunk_sizes_states[-extra:] += 1
        assert np.sum(chunk_sizes_states) == n_states
                
        # determine points chunks:        
        n_chunks_targets = 1
        chunk_sizes_targets = [n_targets]
        if n_targets > 1:
            chunk_size_targets = min(n_targets, self.chunk_size_points)
            n_chunks_targets = max(int(n_targets/chunk_size_targets), 1)
            chunk_size_targets = int(n_targets/n_chunks_targets)
            chunk_sizes_targets = np.full(n_chunks_targets, chunk_size_targets, dtype=np.int32)
            extra = n_targets - n_chunks_targets*chunk_size_targets
            if extra > 0:
                chunk_sizes_targets[-extra:] += 1
            assert np.sum(chunk_sizes_targets) == n_targets

        return n_procs, chunk_sizes_states, chunk_sizes_targets
                     
    def get_chunk_input_data(
        self,
        algo,
        model_data, 
        farm_data, 
        point_data, 
        chunki_states, 
        chunki_points,
        states_i0_i1,
        targets_i0_i1,
        out_vars,
        iterative,
        chunk_store,
    ):
        """
        Extracts the data for a single chunk calculation
        
        Parameters
        ----------
        algo: foxes.core.Algorithm
            The algorithm object
        model_data: xarray.Dataset
            The initial model data
        farm_data: xarray.Dataset
            The initial farm data
        point_data: xarray.Dataset
            The initial point data
        chunki_states: int
            The index of the states chunk
        chunki_points: int
            The index of the targets chunk
        states_i0_i1: tuple
            The (start, end) values of the states
        targets_i0_i1: tuple
            The (start, end) values of the targets     
        out_vars: list of str
            Names of the output variables
        iterative: bool
            Flag for use within the iterative algorithm
        chunk_store: foxes.utils.Dict
            The chunk store from the algorithm
            
        Returns
        -------
        data: list of foxes.core.Data
            Either [mdata, fdata] or [mdata, fdata, tdata]
        
        """
        # prepare:
        i0_states, i1_states = states_i0_i1
        i0_targets, i1_targets = targets_i0_i1
        s_states = np.s_[i0_states:i1_states]
        s_targets = np.s_[i0_targets:i1_targets]
        
        # create mdata:
        mdata = MData.from_dataset(
            model_data, s_states=s_states, loop_dims=[FC.STATE], copy=False)
        
        # create fdata:
        if point_data is None:
            def cb(data, dims):
                n_states = i1_states - i0_states
                for o in set(out_vars).difference(data.keys()):
                    data[o] = np.full((n_states, algo.n_turbines), np.nan, dtype=FC.DTYPE)
                    dims[o] = (FC.STATE, FC.TURBINE)
        else:
            cb = None
        fdata = FData.from_dataset(
            farm_data, mdata=mdata, s_states=s_states, callback=cb,
            loop_dims=[FC.STATE], copy=False)
    
        # create tdata:
        tdata = None
        if point_data is not None:
            def cb(data, dims):
                n_states = i1_states - i0_states
                n_targets = i1_targets - i0_targets
                for o in set(out_vars).difference(data.keys()):
                    data[o] = np.full((n_states, n_targets, 1), np.nan, dtype=FC.DTYPE)
                    dims[o] = (FC.STATE, FC.TARGET, FC.TPOINT)
            tdata = TData.from_dataset(
                point_data, mdata=mdata, s_states=s_states, s_targets=s_targets,
                callback=cb, loop_dims=[FC.STATE, FC.TARGET], copy=False)
        del cb

        # set chunk store data:
        key = (chunki_states, chunki_points)
        algo.reset_chunk_store()
        if iterative and key in chunk_store:
            algo._chunk_store[key] = chunk_store.pop(key)
            
        return [d for d in [mdata, fdata, tdata] if d is not None]
               
    def combine_results(
        self,
        algo,
        results,
        model_data,
        out_vars,
        out_coords,
        n_chunks_states,
        n_chunks_targets,
        goal_data,
        iterative,
    ):
        """
        Combines chunk results into final Dataset
        
        Parameters
        ----------
        algo: foxes.core.Algorithm
            The algorithm object
        results: dict
            The results from the chunk calculations,
            key: (chunki_states, chunki_targets),
            value: dict with numpy.ndarray values
        model_data: xarray.Dataset
            The initial model data
        out_vars: list of str
            Names of the output variables
        out_coords: list of str
            Names of the output coordinates
        n_chunks_states: int
            The number of states chunks
        n_chunks_targets: int
            The number of targets chunks
        goal_data: foxes.core.Data
            Either fdata or tdata
        iterative: bool
            Flag for use within the iterative algorithm
              
        Returns
        -------
        ds: xarray.Dataset
            The final results dataset
            
        """
        self.print("Combining results", level=2)
        pbar = tqdm(total=len(out_vars)) if self.verbosity > 1 else None
        data_vars = {}
        for v in out_vars:
            if v in results[(0, 0)][0]:
                data_vars[v] = [out_coords, []]
                
                if n_chunks_targets == 1:
                    alls=0
                    for chunki_states in range(n_chunks_states):
                        r, cstore = results[(chunki_states, 0)]
                        data_vars[v][1].append(r[v])
                        alls += data_vars[v][1][-1].shape[0]
                        if iterative:
                            algo._chunk_store.update(cstore)
                else:
                    for chunki_states in range(n_chunks_states):
                        tres = []
                        for chunki_points in range(n_chunks_targets):
                            r, cstore = results[(chunki_states, chunki_points)]
                            tres.append(r[v])
                            if iterative:
                                algo._chunk_store.update(cstore)
                        data_vars[v][1].append(np.concatenate(tres, axis=1))
                    del tres
                del r, cstore
                data_vars[v][1] = np.concatenate(data_vars[v][1], axis=0)
            else:
                data_vars[v] = (goal_data[v].dims, goal_data[v].to_numpy())
                
            if pbar is not None:
                pbar.update()
        del results
        if pbar is not None:
            pbar.close()

        if not iterative or algo.final_iteration:
            algo.reset_chunk_store()
            
        coords = {}
        if FC.STATE in out_coords and FC.STATE in model_data.coords:
            coords[FC.STATE] = model_data[FC.STATE].to_numpy()
            
        return Dataset(
            coords=coords, 
            data_vars={v: tuple(d) for v, d in data_vars.items()},
        )
        
    @abstractmethod
    def run_calculation(
        self, 
        algo,
        model, 
        model_data=None, 
        farm_data=None, 
        point_data=None, 
        out_vars=[],
        **calc_pars,
    ):
        """
        Runs the model calculation
        
        Parameters
        ----------
        algo: foxes.core.Algorithm
            The algorithm object
        model: foxes.core.DataCalcModel
            The model that whose calculate function 
            should be run
        model_data: xarray.Dataset
            The initial model data
        farm_data: xarray.Dataset
            The initial farm data
        point_data: xarray.Dataset
            The initial point data
        out_vars: list of str, optional
            Names of the output variables
        calc_pars: dict, optional
            Additional parameters for the model.calculate()
        
        Returns
        -------
        results: xarray.Dataset
            The model results
            
        """
        n_states = model_data.sizes[FC.STATE]
        if point_data is None:
            self.print(f"Calculating {n_states} states for {algo.n_turbines} turbines")
        else:
            self.print(f"Calculating data at {point_data.sizes[FC.TARGET]} points for {n_states} states")
        if not self.initialized:
            raise ValueError(f"Engine '{type(self).__name__}' not initialized")

    @classmethod
    def new(cls, engine_type, *args, **kwargs):
        """
        Run-time engine factory.

        Parameters
        ----------
        engine_type: str
            The selected derived class name
        args: tuple, optional
            Additional parameters for constructor
        kwargs: dict, optional
            Additional parameters for constructor

        """

        if engine_type is None:
            return None

        allc = all_subclasses(cls)
        found = engine_type in [scls.__name__ for scls in allc]

        if found:
            for scls in allc:
                if scls.__name__ == engine_type:
                    return scls(*args, **kwargs)

        else:
            estr = "engine type '{}' is not defined, available types are \n {}".format(
                engine_type, sorted([i.__name__ for i in allc])
            )
            raise KeyError(estr)

def get_engine(error=True, default=True):
    """
    Gets the global calculation engine
    
    Parameters
    ----------
    error: bool
        Flag for raising ValueError if no
        engine is found
    default: bool or dict or Engine
        Set default engine if not set yet
    
    Returns
    -------
    engine: foxes.core.Engine
        The foxes calculation engine
        
    """
    engine = __global_engine_data__["engine"]
    if engine is None:
        if isinstance(default, dict):
            engine = Engine.new(**default)
            print(f"Selecting default engine '{engine}'")
            engine.initialize()
            return engine
        elif isinstance(default, Engine):
            print(f"Selecting default engine '{default}'")
            default.initialize()
            return default
        elif isinstance(default, bool) and default:
            engine = Engine.new(engine_type="MultiprocessEngine")
            print(f"Selecting default engine '{engine}'")
            engine.initialize()
            return engine
        elif error:
            raise ValueError("Engine not found.")
    return engine
