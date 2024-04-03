import numpy as np

from foxes.models.wake_models.gaussian import GaussianWakeModel
import foxes.variables as FV
import foxes.constants as FC


class Bastankhah2014(GaussianWakeModel):
    """
    The Bastankhah 2014 wake model

    Notes
    -----
    Reference:
    "A new analytical model for wind-turbine wakes"
    Majid Bastankhah, Fernando Porté-Agel
    https://doi.org/10.1016/j.renene.2014.01.002

    Attributes
    ----------
    k: float, optional
        The wake growth parameter k. If not given here
        it will be searched in the farm data.
    sbeta_factor: float
        Factor multiplying sbeta
    k_var: str
        The variable name for k
    induction: foxes.core.AxialInductionModel or str
        The induction model

    :group: models.wake_models.wind

    """

    def __init__(
        self,
        superposition,
        k=None,
        sbeta_factor=0.2,
        k_var=FV.K,
        induction="Madsen",
    ):
        """
        Constructor.

        Parameters
        ----------
        superpositions: dict
            The superpositions. Key: variable name str,
            value: The wake superposition model name,
            will be looked up in model book
        k: float, optional
            The wake growth parameter k. If not given here
            it will be searched in the farm data.
        sbeta_factor: float
            Factor multiplying sbeta
        k_var: str
            The variable name for k
        induction: foxes.core.AxialInductionModel or str
            The induction model

        """
        super().__init__(superpositions={FV.WS: superposition})

        self.sbeta_factor = sbeta_factor
        self.k_var = k_var
        self.induction = induction

        setattr(self, k_var, k)

    def __repr__(self):
        k = getattr(self, self.k_var)
        s = super().__repr__()
        s += f"({self.k_var}={k}, sp={self.superpositions[FV.WS]})"
        return s

    def sub_models(self):
        """
        List of all sub-models

        Returns
        -------
        smdls: list of foxes.core.Model
            All sub models

        """
        return [self.induction]

    def initialize(self, algo, verbosity=0, force=False):
        """
        Initializes the model.

        Parameters
        ----------
        algo: foxes.core.Algorithm
            The calculation algorithm
        verbosity: int
            The verbosity level, 0 = silent
        force: bool
            Overwrite existing data

        """
        if isinstance(self.induction, str):
            self.induction = algo.mbook.axial_induction[self.induction]
        super().initialize(algo, verbosity, force)

    def calc_amplitude_sigma_spsel(
        self,
        algo,
        mdata,
        fdata,
        pdata,
        downwind_index,
        x,
    ):
        """
        Calculate the amplitude and the sigma,
        both depend only on x (not on r).

        Parameters
        ----------
        algo: foxes.core.Algorithm
            The calculation algorithm
        mdata: foxes.core.Data
            The model data
        fdata: foxes.core.Data
            The farm data
        pdata: foxes.core.Data
            The evaluation point data
        downwind_index: int
            The index in the downwind order
        x: numpy.ndarray
            The x values, shape: (n_states, n_points)

        Returns
        -------
        amsi: tuple
            The amplitude and sigma, both numpy.ndarray
            with shape (n_sp_sel,)
        sp_sel: numpy.ndarray of bool
            The state-point selection, for which the wake
            is non-zero, shape: (n_states, n_points)

        """
        # get ct:
        ct = self.get_data(
            FV.CT,
            FC.STATE_POINT,
            lookup="w",
            algo=algo,
            fdata=fdata,
            pdata=pdata,
            downwind_index=downwind_index,
        )

        # select targets:
        sp_sel = (x > 1e-5) & (ct > 0.0)
        if np.any(sp_sel):
            # apply selection:
            x = x[sp_sel]
            ct = ct[sp_sel]

            # get D:
            D = self.get_data(
                FV.D,
                FC.STATE_POINT,
                lookup="w",
                algo=algo,
                fdata=fdata,
                pdata=pdata,
                downwind_index=downwind_index,
            )
            D = D[sp_sel]

            # get k:
            k = self.get_data(
                self.k_var,
                FC.STATE_POINT,
                lookup="sw",
                algo=algo,
                fdata=fdata,
                pdata=pdata,
                downwind_index=downwind_index,
            )
            k = k[sp_sel]

            # calculate sigma:
            # beta = 0.5 * (1 + np.sqrt(1.0 - ct)) / np.sqrt(1.0 - ct)
            a = self.induction.ct2a(ct)
            beta = (1 - a) / (1 - 2 * a)
            sigma = k * x + self.sbeta_factor * np.sqrt(beta) * D
            del beta, a

            # calculate amplitude:
            ct_eff = ct / (8 * (sigma / D) ** 2)
            ampld = np.maximum(-2 * self.induction.ct2a(ct_eff), -1)

        # case no targets:
        else:
            sp_sel = np.zeros_like(x, dtype=bool)
            n_sp = np.sum(sp_sel)
            ampld = np.zeros(n_sp, dtype=FC.DTYPE)
            sigma = np.zeros(n_sp, dtype=FC.DTYPE)

        return {FV.WS: (ampld, sigma)}, sp_sel
