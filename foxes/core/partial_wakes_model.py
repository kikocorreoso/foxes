from abc import abstractmethod
import numpy as np

from foxes.core.model import Model
import foxes.variables as FV

class PartialWakesModel(Model):

    def __init__(self, wake_models=None, wake_frame=None):
        super().__init__()

        self.wake_models = wake_models
        self.wake_frame  = wake_frame

    def initialize(self, algo):

        if self.wake_models is None:
            self.wake_models = algo.wake_models
        if self.wake_frame is None:
            self.wake_frame = algo.wake_frame

        if not self.wake_frame.initialized:
            self.wake_frame.initialize(algo)
        for w in self.wake_models:
            if not w.initialized:
                w.initialize(algo)

        super().initialize(algo)

    @abstractmethod
    def n_wake_points(self, algo, mdata, fdata):
        pass
    
    def new_wake_deltas(self, algo, mdata, fdata):
        n_points    = self.n_wake_points(algo, mdata, fdata)
        wake_deltas = {}
        for w in self.wake_models:
            w.init_wake_deltas(algo, mdata, fdata, n_points, wake_deltas)
        return wake_deltas

    @abstractmethod
    def contribute_to_wake_deltas(self, algo, mdata, fdata, 
                            states_source_turbine, wake_deltas):
        pass

    @abstractmethod
    def evaluate_results(self, algo, mdata, fdata, wake_deltas, states_turbine):
        pass
