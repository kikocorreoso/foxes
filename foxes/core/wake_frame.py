from abc import abstractmethod

from foxes.core.model import Model

class WakeFrame(Model):
    """
    Abstract base class for wake frames.

    Wake frames translate global coordinates into
    wake frame coordinates, which are then evaluated
    by wake models.

    """

    @abstractmethod
    def get_wake_coos(self, algo, mdata, fdata, states_source_turbine, points):
        """
        Calculate wake coordinates.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        mdata : foxes.core.Data
            The model data
        fdata : foxes.core.Data
            The farm data
        states_source_turbine : numpy.ndarray
            For each state, one turbine index for the
            wake causing turbine. Shape: (n_states,)
        points : numpy.ndarray
            The evaluation points, shape: (n_states, n_points, 3)
        
        Returns
        -------
        wake_coos : numpy.ndarray
            The wake coordinates, shape: (n_states, n_points, 3)

        """
        pass
