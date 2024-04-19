import numpy as np

from foxes.core import FarmDataModel, Data


class FarmWakesCalculation(FarmDataModel):
    """
    This model calculates wakes effects on farm data.

    Attributes
    ----------
    urelax: foxes.algorithms.iterative.models.URelax
        The under-relaxation model

    :group: algorithms.iterative.models

    """

    def __init__(self, urelax=None):
        """
        Constructor.

        Parameters
        ----------
        urelax: foxes.algorithms.iterative.models.URelax, optional
            The under-relaxation model

        """
        super().__init__()
        self.urelax = urelax

    def output_farm_vars(self, algo):
        """
        The variables which are being modified by the model.

        Parameters
        ----------
        algo: foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        output_vars: list of str
            The output variable names

        """
        ovars = algo.rotor_model.output_farm_vars(
            algo
        ) + algo.farm_controller.output_farm_vars(algo)
        return list(dict.fromkeys(ovars))

    def sub_models(self):
        """
        List of all sub-models

        Returns
        -------
        smdls: list of foxes.core.Model
            All sub models

        """
        return [] if self.urelax is None else [self.urelax]

    def calculate(self, algo, mdata, fdata):
        """ "
        The main model calculation.

        This function is executed on a single chunk of data,
        all computations should be based on numpy arrays.

        Parameters
        ----------
        algo: foxes.core.Algorithm
            The calculation algorithm
        mdata: foxes.core.Data
            The model data
        fdata: foxes.core.Data
            The farm data

        Returns
        -------
        results: dict
            The resulting data, keys: output variable str.
            Values: numpy.ndarray with shape (n_states, n_turbines)

        """
        # prepare:
        n_turbines = mdata.n_turbines

        # generate all wake evaluation points
        # and all wake deltas, both storing as
        # (n_states, n_order, n_rpoints)
        wpoints = {}
        for wname, wmodel in algo.wake_models.items():
            pwake = algo.partial_wakes[wname]
            if pwake.name not in wpoints:
                wpoints[pwake.name] = pwake.get_wake_points(
                    algo, mdata, fdata)

        def _get_wdata(tdata_all, wdeltas, s):
            tdata = tdata_all.get_slice(s)
            wdelta = {v: d[s] for v, d in wdeltas.items()}
            return tdata, wdelta

        def _evaluate(algo, mdata, fdata, wdeltas, oi, wmodel, pwake):
            print("FWAKECALCIT EVAL",wdeltas["WS"])
            pwake.evaluate_results(
                algo, mdata, fdata, wdeltas, wmodel, oi)
            res = algo.farm_controller.calculate(
                algo, mdata, fdata, pre_rotor=False, downwind_index=oi)
            fdata.update(res)

            if self.urelax is not None:
                res = self.urelax.calculate(algo, mdata, fdata, oi)
                for v, d in res.items():
                    fdata[v][:, oi] = d

        for wname, wmodel in algo.wake_models.items():
            pwake = algo.partial_wakes[wname]
            tdata_all = Data.from_tpoints(rpoints=wpoints[pwake.name])
            wdeltas = pwake.new_wake_deltas(algo, mdata, fdata, 
                                            wmodel, wpoints[pwake.name])

            for oi in range(n_turbines):
                
                if oi > 0:
                    tdata, wdelta = _get_wdata(tdata_all, wdeltas, 
                                               np.s_[:, :oi])
                    pwake.contribute(algo, mdata, fdata, 
                                        tdata, oi, wdelta, wmodel)
                    print("FWAKECALCIT CONTR",oi,wdeltas["WS"])

                if oi < n_turbines - 1:
                    tdata, wdelta = _get_wdata(tdata_all, wdeltas, 
                                               np.s_[:, oi+1:])
                    pwake.contribute(algo, mdata, fdata,
                                        tdata, oi, wdelta, wmodel)
                    print("FWAKECALCIT CONTR",oi,wdeltas["WS"])
                _evaluate(algo, mdata, fdata, wdeltas, oi, wmodel, pwake)
            
        return {v: fdata[v] for v in self.output_farm_vars(algo)}
