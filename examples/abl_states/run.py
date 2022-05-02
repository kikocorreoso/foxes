
import numpy as np
import time
import argparse
import dask
from dask.diagnostics import ProgressBar

import foxes
import foxes.variables as FV
from dask.distributed import Client

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("sfile", help="The states input file")
    parser.add_argument("lfile", help="The turbine layout file")
    parser.add_argument("-c", "--chunksize", help="The maximal chunk size", type=int, default=1000)
    parser.add_argument("-s", "--scheduler", help="The scheduler choice", default=None)
    parser.add_argument("-w", "--n_workers", help="The number of workers for distributed run", type=int, default=None)
    parser.add_argument("-t", "--threads_per_worker", help="The number of threads per worker for distributed run", type=int, default=None)
    parser.add_argument("--nodask", help="Use numpy arrays instead of dask arrays", action="store_true")
    args  = parser.parse_args()
    
    cks = None if args.nodask else {FV.STATE: args.chunksize}
    if args.scheduler == 'distributed':
        client = Client(n_workers=args.n_workers, threads_per_worker=args.threads_per_worker)
        print(f"\n{client}")
        print(f"Dashboard: {client.dashboard_link}\n")

    with dask.config.set(scheduler=args.scheduler):

        mbook = foxes.models.ModelBook()
        mbook.turbine_types["TOYT"] = foxes.models.turbine_types.PCtFile(
                                        name="TOYT", filepath="toyTurbine.csv", D=120.)

        states = foxes.input.states.StatesTable(
            data_source=args.sfile,
            output_vars=[FV.WS, FV.WD, FV.TI, FV.RHO, FV.MOL],
            var2col={FV.WS: "ws", FV.WD: "wd", FV.TI: "ti", FV.MOL: "mol"},
            fixed_vars={FV.RHO: 1.225, FV.Z0: 0.05, FV.H: 100.0},
            profiles={FV.WS: "ABLLogWsProfile"}
        )

        farm = foxes.WindFarm()
        foxes.input.farm_layout.add_from_file(
            farm,
            args.lfile,
            col_x="x",
            col_y="y",
            col_H="H",
            turbine_models=["TOYT"]
        )
        
        algo = foxes.algorithms.Downwind(
                    mbook,
                    farm,
                    states=states,
                    rotor_model="centre",
                    turbine_order="order_wd",
                    wake_models=['Jensen_linear_k007'],
                    wake_frame="mean_wd",
                    partial_wakes_model="rotor_points",
                    chunks=cks
                )
        
        time0 = time.time()
        
        with ProgressBar():
            farm_results = algo.calc_farm()

        time1 = time.time()
        print("\nCalc time =",time1 - time0, "\n")

        print(farm_results)
    
    fr = farm_results.to_dataframe()
    print(fr[[FV.WD, FV.H, FV.AMB_REWS, FV.REWS, FV.AMB_P, FV.P]])

