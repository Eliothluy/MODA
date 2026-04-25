import argparse
import json
import numpy as np
from environments.rslaq_env import RslaqEnv

if __name__ == '__main__':
    #######################
    # Parse arguments #
    #######################
    parser = argparse.ArgumentParser(description="Run the RSLAQ environment")
    parser.add_argument("--config", type=str, default="/home/eliothluy/Documentos/artigo_jussi/ns-o-ran-gym/src/environments/scenario_configurations/rslaq_use_case.json",
                        help="Path to the configuration file")
    parser.add_argument("--output_folder", type=str, default="output",
                        help="Path to the output folder")
    parser.add_argument("--ns3_path", type=str, default="/home/eliothluy/Documentos/artigo_jussi/ns-3-dev/",
                        help="Path to the ns-3 mmWave O-RAN environment")
    parser.add_argument("--num_steps", type=int, default=1000,
                        help="Number of steps to run in the environment")
    parser.add_argument("--optimized", action="store_true",
                        help="Enable optimization mode")

    args = parser.parse_args()

    configuration_path = args.config
    output_folder = args.output_folder
    ns3_path = args.ns3_path
    num_steps = args.num_steps
    optimized = args.optimized

    try:
        with open(configuration_path) as params_file:
            params = params_file.read()
    except FileNotFoundError:
        print(f"Cannot open '{configuration_path}' file, exiting")
        exit(-1)

    scenario_configuration = json.loads(params)

    print('Creating RSLAQ Environment')
    env = RslaqEnv(ns3_path=ns3_path, scenario_configuration=scenario_configuration, 
                          output_folder=output_folder, optimized=optimized)

    print('Environment Created!')

    print('Launch reset ', end='', flush=True)
    obs, info = env.reset()
    print('done')
    
    print(f'First set of observations {obs}')
    print(f'Info {info}')

    # Action logic
    for step in range(2, num_steps):
        # Build heuristic action: per-slice PRB allocation [dedicated, min, max]
        # Slice 0 (eMBB): high throughput demand -> larger PRB allocation
        # Slice 1 (URLLC): ultra-reliable, low latency -> moderate PRB allocation
        # Slice 2 (MTC): massive IoT, low rate -> smaller PRB allocation
        model_action = np.array([
            [33.33, 20.0, 60.0],   # eMBB slice:  dedicated=33.33%, min=20%, max=60%
            [33.33, 10.0, 40.0],   # URLLC slice: dedicated=33.33%, min=10%, max=40%
            [33.34,  5.0, 20.0],   # MTC slice:   dedicated=33.34%, min= 5%, max=20%
        ])
         
        print(f'Step {step} ', end='', flush=True)
        obs, reward, terminated, truncated, info = env.step(model_action)

        print('done', flush=True)

        print(f'Status t = {step}')
        print(f'Actions {env._compute_action(model_action)}') 
        print(f'Observations {obs}')
        print(f'Reward {reward}')
        print(f'Terminated {terminated}')
        print(f'Truncated {truncated}')
        print(f'Info {info}')

        # If the environment is over, exit
        if terminated:
            break

        # If the episode is up (environment still running), then start another one
        if truncated:
            break # We don't want this outside the training
            obs, info = env.reset()
