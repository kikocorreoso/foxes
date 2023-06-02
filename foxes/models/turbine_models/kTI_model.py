import numpy as np

from foxes.core import TurbineModel
import foxes.variables as FV
import foxes.constants as FC


class kTI(TurbineModel):
    """
    Calculates the wake model parameter `k`
    as a linear function of `TI`.

    Parameters
    ----------
    kTI : float, optional
        Uniform value for `kTI`. If not given it
        will be searched in farm data
    kb : float, optional
        Uniform value for `kb`. If not given it
        will be searched in farm data, and zero by default
    ti_var : str
        The `TI` variable name
    ti_val : float, optional
        The uniform value of `TI`. If not given it
        will be searched in farm data
    k_var : str
        The variable name for k

    Attributes
    ----------
    ti_var : str
        The `TI` variable name
    k_var : str
        The variable name for k

    """

    def __init__(self, kTI=None, kb=None, ti_var=FV.TI, ti_val=None, k_var=FV.K):
        super().__init__()

        self.ti_var = ti_var
        self.k_var = k_var
        setattr(self, ti_var, ti_val)
        setattr(self, FV.KTI, kTI)
        setattr(self, FV.KB, 0 if kb is None else kb)

    def __repr__(self):
        return super().__repr__() + f"({self.k_var}, kTI={getattr(self, FV.KTI)}, ti={self.ti_var})"

    def output_farm_vars(self, algo):
        """
        The variables which are being modified by the model.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm

        Returns
        -------
        output_vars : list of str
            The output variable names

        """
        return [self.k_var]

    def calculate(self, algo, mdata, fdata, st_sel):
        """ "
        The main model calculation.

        This function is executed on a single chunk of data,
        all computations should be based on numpy arrays.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        mdata : foxes.core.Data
            The model data
        fdata : foxes.core.Data
            The farm data
        st_sel : numpy.ndarray of bool
            The state-turbine selection,
            shape: (n_states, n_turbines)

        Returns
        -------
        results : dict
            The resulting data, keys: output variable str.
            Values: numpy.ndarray with shape (n_states, n_turbines)

        """
        kTI = self.get_data(FV.KTI, fdata, st_sel)
        kb = self.get_data(FV.KB, fdata, st_sel)
        ti = self.get_data(self.ti_var, fdata, st_sel)

        k = fdata.get(
            self.k_var, np.zeros((fdata.n_states, fdata.n_turbines), dtype=FC.DTYPE)
        )

        k[st_sel] = kTI * ti + kb

        return {self.k_var: k}
