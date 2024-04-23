from foxes.core import PartialWakesModel

class RotorPoints(PartialWakesModel):
    """
    Partial wakes calculation directly by the
    rotor model.

    :group: models.partial_wakes

    """

    def get_wake_points(self, algo, mdata, fdata):
        """
        Get the wake calculation points.

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
        rpoints: numpy.ndarray
            All rotor points, shape: (n_states, n_targets, n_rpoints, 3)

        """
        rotor = algo.rotor_model
        return rotor.from_data_or_store(rotor.RPOINTS, algo, mdata)

    def finalize_wakes(
        self,
        algo, 
        mdata, 
        fdata, 
        amb_res, 
        wake_deltas, 
        wmodel, 
        downwind_index
    ):
        """
        Updates the wake_deltas at the selected target
        downwind index.

        Modifies wake_deltas on the fly.

        Parameters
        ----------
        algo: foxes.core.Algorithm
            The calculation algorithm
        mdata: foxes.core.Data
            The model data
        fdata: foxes.core.Data
            The farm data
        amb_res: dict
            The ambient results at the target points
            of all rotors. Key: variable name, value
            np.ndarray of shape: 
            (n_states, n_turbines, n_rotor_points)
        wake_deltas: dict
            The wake deltas. Key: variable name,
            value: np.ndarray of shape 
            (n_states, n_turbines, n_tpoints)
        wmodel: foxes.core.WakeModel
            The wake model
        downwind_index: int
            The index in the downwind order
        
        Returns
        -------
        final_wake_deltas: dict
            The final wake deltas at the selected downwind 
            turbines. Key: variable name, value: np.ndarray 
            of shape (n_states, n_rotor_points)

        """
        ares = {v: d[:, downwind_index, None] for v, d in amb_res.items()}
        wdel = {v: d[:, downwind_index, None].copy() for v, d in wake_deltas.items()}
        wmodel.finalize_wake_deltas(algo, mdata, fdata, ares, wdel)

        return {v: d[:, 0] for v, d in wdel.items()}
