import dask
import numpy as np
import xarray as xr
from distributed import Client, LocalCluster, progress
from dask.diagnostics import ProgressBar
from dask_jobqueue import SLURMCluster
from copy import deepcopy
from os import cpu_count
from tqdm import tqdm

from foxes.core import Engine, MData, FData, TData
import foxes.variables as FV
import foxes.constants as FC

def _wrap_calc(
    *ldata,
    algo,
    dvars,
    lvars,
    ldims,
    evars,
    edims,
    edata,
    loop_dims,
    out_vars,
    out_coords,
    calc_pars,
    init_vars,
    ensure_variables,
    calculate,
):
    """
    Wrapper that mitigates between apply_ufunc and `calculate`.
    """
    n_prev = len(init_vars)
    if n_prev:
        prev = ldata[:n_prev]
        ldata = ldata[n_prev:]

    # reconstruct original data:
    data = []
    for i, hvars in enumerate(dvars):
        v2l = {v: lvars.index(v) for v in hvars if v in lvars}
        v2e = {v: evars.index(v) for v in hvars if v in evars}

        hdata = {v: ldata[v2l[v]] if v in v2l else edata[v2e[v]] for v in hvars}
        hdims = {v: ldims[v2l[v]] if v in v2l else edims[v2e[v]] for v in hvars}

        if i == 0:
            data.append(MData(data=hdata, dims=hdims, loop_dims=loop_dims))
        elif i == 1:
            data.append(FData(data=hdata, dims=hdims, loop_dims=loop_dims))
        elif i == 2:
            data.append(TData(data=hdata, dims=hdims, loop_dims=loop_dims))
        else:
            raise NotImplementedError(
                f"Not more than 3 data sets implemented, found {len(dvars)}"
            )

        del hdata, hdims, v2l, v2e

    # deduce output shape:
    oshape = []
    for li, l in enumerate(out_coords):
        for i, dims in enumerate(ldims):
            if l in dims:
                oshape.append(ldata[i].shape[dims.index(l)])
                break
        if len(oshape) != li + 1:
            raise ValueError(f"Failed to find loop dimension")

    # add zero output data arrays:
    odims = {v: tuple(out_coords) for v in out_vars}
    odata = {
        v: (
            np.full(oshape, np.nan, dtype=FC.DTYPE)
            if v not in init_vars
            else prev[init_vars.index(v)].copy()
        )
        for v in out_vars
        if v not in data[-1]
    }

    if len(data) == 1:
        data.append(FData(odata, odims, loop_dims))
    else:
        odata.update(data[-1])
        odims.update(data[-1].dims)
        if len(data) == 2:
            data[-1] = FData(odata, odims, loop_dims)
        else:
            data[-1] = TData(odata, odims, loop_dims)
    del odims, odata

    # link chunk state indices from mdata to fdata and tdata:
    if FC.STATE in data[0]:
        for d in data[1:]:
            d[FC.STATE] = data[0][FC.STATE]

    # link weights from mdata to fdata:
    if FV.WEIGHT in data[0]:
        data[1][FV.WEIGHT] = data[0][FV.WEIGHT]
        data[1].dims[FV.WEIGHT] = data[0].dims[FV.WEIGHT]

    # run model calculation:
    ensure_variables(algo, *data)
    results = calculate(algo, *data, **calc_pars)

    # replace missing results by first input data with matching shape:
    missing = set(out_vars).difference(results.keys())
    if len(missing):
        found = set()
        for v in missing:
            for dta in data:
                if v in dta and dta[v].shape == tuple(oshape):
                    results[v] = dta[v]
                    found.add(v)
                    break
        missing -= found
        if len(missing):
            raise ValueError(
                f"Missing results {list(missing)}, expected shape {oshape}"
            )
    del data

    # create output:
    n_vars = len(out_vars)
    data = np.zeros(oshape + [n_vars], dtype=FC.DTYPE)
    for v in out_vars:
        data[..., out_vars.index(v)] = results[v]

    return data
    
class DaskEngine(Engine):
    """
    The dask engine for foxes calculations.
    
    Parameters
    ----------
    dask_config: dict
        The dask configuration parameters
    cluster: str
        The dask cluster choice: 'local' or 'slurm'
    cluster_pars: dict
        Parameters for the cluster
    client_pars: dict
        Parameters for the client of the cluster
    progress_bar: bool
        Flag for showing progress bar
    n_procs: int
        The number of cpus
            
    :group: engines
    
    """
    def __init__(
        self, 
        dask_config={},
        cluster=None, 
        cluster_pars={}, 
        client_pars={}, 
        n_procs=None,
        progress_bar=True,
        **kwargs,
    ):
        """
        Constructor.
        
        Parameters
        ----------
        dask_config: dict, optional
            The dask configuration parameters
        cluster: str, optional
            The dask cluster choice: 'local' or 'slurm'
        cluster_pars: dict
            Parameters for the cluster
        client_pars: dict
            Parameters for the client of the cluster
        n_procs: int, optional
            The number of processes to be used,
            or None for automatic
        progress_bar: bool
            Flag for showing progress bar
        kwargs: dict, optional
            Additional parameters for the base class
            
        """
        super().__init__(**kwargs)
        self.dask_config = dask_config
        self.cluster = cluster
        self.cluster_pars = cluster_pars
        self.client_pars = client_pars
        self.progress_bar = progress_bar
        self.n_procs = n_procs if n_procs is not None else cpu_count()
        
        self._cluster = None
        self._client = None

    def initialize(self):
        """
        Initializes the engine.
        """       
        if self.cluster == "local":         
            self.print("Launching local dask cluster..")

            self._cluster = LocalCluster(n_workers=self.n_procs, **self.cluster_pars)
            self._client = Client(self._cluster, **self.client_pars)
            self.dask_config["scheduler"] = "distributed"

            self.print(self._cluster)
            self.print(f"Dashboard: {self._client.dashboard_link}\n")
            
        elif self.cluster == "slurm":
            self.print("Launching dask cluster on HPC using SLURM..")

            cargs = deepcopy(self.cluster_pars)
            nodes = cargs.pop("nodes", 1)
            self._cluster = SLURMCluster(cores=self.n_procs, **cargs)
            self._cluster.scale(jobs=nodes)
            self._client = Client(self._cluster, **self.client_pars)
            self.dask_config["scheduler"] = "distributed"

            self.print(self._cluster)
            self.print(f"Dashboard: {self._client.dashboard_link}\n")
        
        if self.progress_bar:
            self._pbar = ProgressBar(minimum=2)
            self._pbar.register()

        dask.config.set(**self.dask_config)
        
        super().initialize()

    def chunk_data(self, data):
        """
        Applies the selected chunking
        
        Parameters
        ----------
        data: xarray.Dataset
            The data to be chunked
        
        Returns
        -------
        data: xarray.Dataset
            The chunked data
        
        """
        cks = {}
        cks[FC.STATE] = min(data.sizes[FC.STATE], self.chunk_size_states)
        if FC.TARGET in data.sizes:
            cks[FC.TARGET] = min(data.sizes[FC.TARGET], self.chunk_size_points)
            
        if len(set(cks.keys()).intersection(data.coords.keys())):
            return data.chunk({v: d for v, d in cks.items() if v in data.coords})
        else:
            return data
    
    def run_calculation(
        self, 
        algo,
        model, 
        model_data=None, 
        farm_data=None, 
        point_data=None, 
        out_vars=[],
        sel=None,
        isel=None,
        persist=True,
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
        sel: dict, optional
            Selection of coordinate subsets
        isel: dict, optional
            Selection of coordinate subsets index values
        persist: bool
            Flag for persisting xarray Dataset objects
        calc_pars: dict, optional
            Additional parameters for the model.calculate()
        
        Returns
        -------
        results: xarray.Dataset
            The model results
            
        """
        # subset selection:
        model_data, farm_data, point_data = self.select_subsets(
            model_data, farm_data, point_data, sel=sel, isel=isel)
        
        # basic checks:
        super().run_calculation(algo, model, model_data, farm_data,
                                point_data, **calc_pars)
        
        # find chunk sizes, if not given:
        chunk_size_states0 = self.chunk_size_states
        chunk_size_points0 = self.chunk_size_points
        n_procs = len(self._client.scheduler_info()['workers']) if self._cluster is not None else self.n_procs
        if self.chunk_size_states is None: 
            self.chunk_size_states = max(int(model_data.sizes[FC.STATE]/n_procs), 1)
        if self.chunk_size_points is None and point_data is not None:
            self.chunk_size_points = max(int(point_data.sizes[FC.TARGET]/n_procs), 1)

        # prepare:
        out_coords = model.output_coords()
        loop_dims = [d for d in self.loop_dims if d in out_coords]
        loopd = set(loop_dims)
        
        # extract loop-var dependent and independent data:
        ldata = []
        lvars = []
        ldims = []
        edata = []
        evars = []
        edims = []
        dvars = []
        ivars = []
        idims = []
        data = [self.chunk_data(d) for d in [model_data, farm_data, point_data] if d is not None]
        for ds in data:
            
            hvarsl = [v for v, d in ds.items() if len(loopd.intersection(d.dims))]
            ldata += [ds[v] for v in hvarsl]
            ldims += [ds[v].dims for v in hvarsl]
            lvars += hvarsl

            hvarse = [v for v in ds.keys() if v not in hvarsl]
            edata += [ds[v].values for v in hvarse]
            edims += [ds[v].dims for v in hvarse]
            evars += hvarse

            for c, d in ds.coords.items():
                if c in loopd:
                    ldata.append(self.chunk_data(xr.DataArray(data=d.values, coords={c: d}, dims=[c])))
                    ldims.append((c,))
                    lvars.append(c)
                else:
                    edata.append(d.values)
                    edims.append((c,))
                    evars.append(c)

            dvars.append(list(ds.keys()) + list(ds.coords.keys()))
        
        # apply persist:
        if persist:
            ldata = [d.persist() for d in ldata]

        # setup dask options:
        dargs = dict(output_sizes={FC.VARS: len(out_vars)})
        out_core_vars = [d for d in out_coords if d not in loop_dims] + [FC.VARS]
        if FC.TURBINE in loopd and FC.TURBINE not in ldims.values():
            dargs["output_sizes"][FC.TURBINE] = algo.n_turbines
            
        # setup arguments for wrapper function:
        out_coords = loop_dims + list(set(out_core_vars).difference([FC.VARS]))
        wargs = dict(
            algo=algo,
            dvars=dvars,
            lvars=lvars,
            ldims=ldims,
            evars=evars,
            edims=edims,
            edata=edata,
            loop_dims=loop_dims,
            out_vars=out_vars,
            out_coords=out_coords,
            calc_pars=calc_pars,
            init_vars=ivars,
            ensure_variables=model.ensure_variables,
            calculate=model.calculate,
        )

        # run parallel computation:
        iidims = [[c for c in d if c not in loopd] for d in idims]
        icdims = [[c for c in d if c not in loopd] for d in ldims]
        results = xr.apply_ufunc(
            _wrap_calc,
            *ldata,
            input_core_dims=iidims + icdims,
            output_core_dims=[out_core_vars],
            output_dtypes=[FC.DTYPE],
            dask="parallelized",
            dask_gufunc_kwargs=dargs,
            kwargs=wargs,
        ).persist()
        
        # main calculation:
        if self._client is not None and self.progress_bar:
            progress(results)
        results = results.compute(num_workers=self.n_procs)

        # reorganize results Dataset:
        results = results.assign_coords({FC.VARS: out_vars}).to_dataset(dim=FC.VARS)

        # reset:
        self.chunk_size_states = chunk_size_states0
        self.chunk_size_points = chunk_size_points0

        # update data by calculation results:
        return results.compute(num_workers=self.n_procs)
    
    def finalize(self):
        """
        Finalizes the engine.
        """
        if self.cluster is not None:
            self.print("\n\nShutting down dask cluster")
            self._client.close()
            self._cluster.close()
        
        if self.progress_bar:
            self._pbar.unregister()
            
        dask.config.refresh()
        
        super().finalize()

def _run_on_cluster(
    algo, 
    model, 
    *data, 
    names,
    dims,
    mdata_size,
    fdata_size,
    loop_dims,
    **cpars):
    """ Helper function running on a cluster """
    
    mdata = MData(
        data={names[i]: data[i] for i in range(mdata_size)},
        dims={names[i]: dims[i] for i in range(mdata_size)},
        loop_dims=loop_dims[0],
    )
    
    fdata_end = mdata_size + fdata_size
    fdata = FData(
        data={names[i]: data[i].copy() for i in range(mdata_size, fdata_end)},
        dims={names[i]: dims[i] for i in range(mdata_size, fdata_end)},
        loop_dims=loop_dims[1],
    )

    tdata = None
    if len(data) >  fdata_end:
        tdata = TData(
            data={names[i]: data[i].copy() for i in range(fdata_end, len(data))},
            dims={names[i]: dims[i] for i in range(fdata_end, len(data))},
            loop_dims=loop_dims[2],
        )

    data = [d for d in [mdata, fdata, tdata] if d is not None]

    return model.calculate(algo, *data, **cpars)

class LocalClusterEngine(DaskEngine):
    """
    The dask engine for foxes calculations on a local cluster.
    
    :group: engines
    
    """
    def __init__(self, *args, chunk_size_points=None, **kwargs):
        """
        Constructor.
        
        Parameters
        ----------
        args: tuple, optional
            Additional parameters for the DaskEngine class
        chunk_size_points: int, optional
            The size of a points chunk
        kwargs: dict, optional
            Additional parameters for the base class
            
        """
        csp = chunk_size_points if chunk_size_points is not None else 10000
        super().__init__(*args, cluster="local", chunk_size_points=csp, **kwargs)
        
    def run_calculation(
        self, 
        algo,
        model, 
        model_data=None, 
        farm_data=None, 
        point_data=None, 
        out_vars=[],
        sel=None,
        isel=None,
        persist=True,
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
        sel: dict, optional
            Selection of coordinate subsets
        isel: dict, optional
            Selection of coordinate subsets index values
        persist: bool
            Flag for persisting xarray Dataset objects
        calc_pars: dict, optional
            Additional parameters for the model.calculate()
        
        Returns
        -------
        results: xarray.Dataset
            The model results
            
        """
        # subset selection:
        model_data, farm_data, point_data = self.select_subsets(
            model_data, farm_data, point_data, sel=sel, isel=isel)
        
        # basic checks:
        Engine.run_calculation(self, algo, model, model_data, farm_data,
                                point_data, **calc_pars)

        # prepare:
        n_states = model_data.sizes[FC.STATE] 
        out_coords = model.output_coords()
        coords = {}
        if FC.STATE in out_coords and FC.STATE in model_data.coords:
            coords[FC.STATE] = model_data[FC.STATE].to_numpy()
        if farm_data is None:
            farm_data = xr.Dataset()
        loop_dims = [d for d in self.loop_dims if d in out_coords]
        loopd = set(loop_dims)
        
        # calculate chunk sizes:
        n_targets = point_data.sizes[FC.TARGET] if point_data is not None else 0
        n_procs, chunk_sizes_states, chunk_sizes_targets = self.calc_chunk_sizes(n_states, n_targets)
        n_chunks_states = len(chunk_sizes_states)
        n_chunks_targets = len(chunk_sizes_targets)
        self.print(f"Selecting n_chunks_states = {n_chunks_states}, n_chunks_targets = {n_chunks_targets}", level=2)
                    
        # prepare chunks:
        n_chunks_all = n_chunks_states*n_chunks_targets
        n_procs = min(n_procs, n_chunks_all)
        falgo = self._client.scatter(algo, broadcast=True)
        fmodel = self._client.scatter(model, broadcast=True)
        cpars = calc_pars#{v: self._client.scatter(d, broadcast=True) for v, d in calc_pars.items()}
        
        # submit chunks:
        self.print(f"Submitting {n_chunks_all} chunks to {n_procs} processes")
        pbar = tqdm(total=n_chunks_all) if self.verbosity > 0 else None
        jobs = {}
        i0_states = 0
        all_data = []
        for chunki_states in range(n_chunks_states):
            i1_states = i0_states + chunk_sizes_states[chunki_states]
            s_states = np.s_[i0_states:i1_states]
            i0_targets = 0          
            for chunki_points in range(n_chunks_targets):
                i1_targets = i0_targets + chunk_sizes_targets[chunki_points]
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

                # scatter data:
                data = []
                names = []
                dims = []
                ldims = [mdata.loop_dims, fdata.loop_dims]
                for k, d in mdata.items():
                    data.append(self._client.scatter(d))
                    names.append(k)
                    dims.append(mdata.dims[k])
                for k, d in fdata.items():
                    data.append(self._client.scatter(d))
                    names.append(k)
                    dims.append(fdata.dims[k])
                if tdata is not None:
                    ldims.append(tdata.loop_dims)
                    for k, d in tdata.items():
                        data.append(self._client.scatter(d))
                        names.append(k)
                        dims.append(tdata.dims[k])
                all_data.append(data)
                          
                # submit model calculation:
                jobs[(chunki_states, chunki_points)] = self._client.submit(
                    _run_on_cluster,
                    falgo, 
                    fmodel,
                    *data,
                    names=names,
                    dims=dims,
                    mdata_size=len(mdata),
                    fdata_size=len(fdata),
                    loop_dims=ldims,
                    **cpars,
                )
                    
                i0_targets = i1_targets
        
                if pbar is not None:
                    pbar.update()
                    
            i0_states = i1_states
            
        del model_data, farm_data, point_data, calc_pars
        if pbar is not None:
            pbar.close()
            
        # wait for results:
        self.print(f"Computing {n_chunks_all} chunks using {n_procs} processes")
        pbar = tqdm(total=n_chunks_all) if n_chunks_all > 1 and self.verbosity > 0 else None
        results = {}
        for chunki_states in range(n_chunks_states):
            for chunki_points in range(n_chunks_targets):
                r = jobs.get((chunki_states, chunki_points))
                results[(chunki_states, chunki_points)] = r.result()
                if pbar is not None:
                    pbar.update()
        if pbar is not None:
            pbar.close()
        del all_data

        # combine results:
        self.print("Combining results", level=2)
        pbar = tqdm(total=len(out_vars)) if self.verbosity > 1 else None
        data_vars = {}
        for v in out_vars:
            data_vars[v] = [out_coords, []]
            
            if n_chunks_targets == 1:
                alls=0
                for chunki_states in range(n_chunks_states):
                    r = results[(chunki_states, 0)]
                    data_vars[v][1].append(r[v])
                    alls += data_vars[v][1][-1].shape[0]
            else:
                for chunki_states in range(n_chunks_states):
                    tres = []
                    for chunki_points in range(n_chunks_targets):
                        r = results[(chunki_states, chunki_points)]
                        tres.append(r[v])
                    data_vars[v][1].append(np.concatenate(tres, axis=1))
                del tres
            data_vars[v][1] = np.concatenate(data_vars[v][1], axis=0)
            
            if pbar is not None:
                pbar.update()
        del results
        if pbar is not None:
            pbar.close()
        
        return xr.Dataset(
            coords=coords, 
            data_vars={v: tuple(d) for v, d in data_vars.items()},
        )

class SlurmClusterEngine(LocalClusterEngine):
    """
    The dask engine for foxes calculations on a SLURM cluster.
    
    :group: engines
    
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor.
        
        Parameters
        ----------
        args: tuple, optional
            Additional parameters for the LocalClusterEngine class
        kwargs: dict, optional
            Additional parameters for the LocalClusterEngine class
            
        """
        super().__init__(*args, **kwargs)
        self.cluster = "slurm"
        