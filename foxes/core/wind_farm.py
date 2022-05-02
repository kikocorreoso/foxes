
class WindFarm:

    def __init__(self, name="MyFarm"):
        self.name     = name
        self.turbines = []
    
    def add_turbine(self, turbine, verbosity=1):
        if turbine.index is None:
            turbine.index = len(self.turbines)
        if turbine.name is None:
            turbine.name = f"T{turbine.index}"
        self.turbines.append(turbine)
        if verbosity > 0:
            print(f"Turbine {turbine.index}, {turbine.name}: {', '.join(turbine.models)}")
    
    @property
    def n_turbines(self):
        return len(self.turbines)

        
