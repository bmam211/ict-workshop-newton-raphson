import pandapower as pp
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.preprocessing import StandardScaler
import pickle
from tqdm import tqdm

class SimpleTwoBus:

    def __init__(self, V_ext, P, Q, G, B, V_init, theta_init):
        '''This class creates a simple 2-bus network.'''
        self.V_ext = V_ext
        self.P = P
        self.Q = Q
        self.G = G
        self.B = B
        self.V_init = V_init
        self.theta_init = theta_init
        self.net = pp.create_empty_network()
        self.create_two_bus_grid()


    def create_two_bus_grid(self):
    
        # Create two buses with initialized voltage and angle
        bus1 = pp.create_bus(self.net, vn_kv=20.0, name="Bus 1")
        bus2 = pp.create_bus(self.net, vn_kv=0.4, name="Bus 2")
    
        # Initialize voltage and angle for buses
        self.net.bus.loc[bus1, 'vm_pu'] = self.V_init[0]
        self.net.bus.loc[bus1, 'va_degree'] = self.theta_init[0]
        self.net.bus.loc[bus2, 'vm_pu'] = self.V_init[1]
        self.net.bus.loc[bus2, 'va_degree'] = self.theta_init[1]
    
        # create a line between the two buses
        pp.create_line_from_parameters(
            self.net,
            from_bus=0,
            to_bus=1,
            length_km=1.0,
            r_ohm_per_km=1/self.G,
            x_ohm_per_km=1/self.B,
            c_nf_per_km=0.0,
            g_us_per_km=0.0,
            max_i_ka=100.0,
        )

        # Create a transformer between the two buses
        # pp.create_transformer(self.net, bus1, bus2, std_type="0.25 MVA 20/0.4 kV")
    
        # Create a load at bus 2 with specified P and Q
        pp.create_load(self.net, bus2, p_mw=self.P, q_mvar=self.Q, name="Load")
    
        # Create an external grid connection at bus 1 with specified G and B
        pp.create_ext_grid(self.net, bus1, vm_pu=self.V_ext, name="Grid Connection")
        
class PowerFlowDataset(Dataset):
    def __init__(self, base_network, num_samples=1000, max_iteration=50, tolerance_mva=1e-8, v_perturb=0.15, theta_perturb=30):
        """
        Initialize the dataset with a base network and number of samples.
       
        Parameters:
        base_network (pandapowerNet): The base pandapower network.
        num_samples (int): Number of samples to generate.
        """
        self.base_net = base_network.deepcopy()  # Ensure base network is not modified
        self.num_samples = num_samples
        self.samples = []
        self.scaler_input = StandardScaler()
        self.scaler_output = StandardScaler()
        self.max_iteration = max_iteration
        self.tolerance_mva = tolerance_mva
        self.v_perturb = v_perturb
        self.theta_perturb = theta_perturb
 
        self.generate_samples()
        
    def compute_residual(self, V_mag, V_ang, Ybus, S):
        V_ang = np.deg2rad(V_ang)
        complex_v = V_mag*(np.exp(V_ang*1j))
        current = Ybus@complex_v
        diag_V = np.diag(complex_v)
        residual = diag_V@np.conj(current) - S
        
        return residual[1:]
 
    def generate_samples(self):
        """
        Generate samples by first running normal power flow and then perturbing it to create ill-conditioning.
        """
        # Run a normal power flow first
        net = self.base_net.deepcopy()
        try:
            pp.runpp(net, max_iteration=100)  # Solve with standard conditions
            # print("Base case solved successfully.")
        except pp.powerflow.LoadflowNotConverged:
            # print("Base case did not converge. Check the network setup.")
            return
       
        # Extract the normal solution
        v_nominal = net.res_bus.vm_pu.values  # Nominal voltage magnitudes
        theta_nominal = net.res_bus.va_degree.values  # Nominal voltage angles
       
        for _ in range(self.num_samples):
            net_ill = self.base_net.deepcopy()  # Keep the network unchanged
 
            # --- Create an ill-conditioned case ---
            v_ill = v_nominal + np.random.uniform(-self.v_perturb, self.v_perturb, len(v_nominal))  # Small perturbation
            theta_ill = theta_nominal + np.random.uniform(-self.theta_perturb, self.theta_perturb, len(theta_nominal))  # Large phase shift
            # p_ill = net_ill.res_bus.p_mw.values + np.random.uniform(-200, 200, len(v_nominal))  # Large power mismatch
 
            try:
                # Re-run power flow with ill-conditioned initialization
                pp.runpp(net_ill,
                         init="auto",
                         init_vm_pu=v_ill,
                         init_va_degree=theta_ill,
                         max_iteration=self.max_iteration,
                         tolerance_mva=self.tolerance_mva)
               
                iterations = net_ill._ppc["iterations"]
                # print(f"Sample {_}: Converged in {iterations} iterations")
 
                # Extract ill-conditioned solution
                Ybus = net_ill._ppc["internal"]["Ybus"].toarray()
                S = net_ill._ppc["internal"]["Sbus"]
                it = net._ppc["iterations"]
                et = net._ppc["et"]
                V_mag = net_ill.res_bus.vm_pu.values
                V_ang = net_ill.res_bus.va_degree.values
                resd = self.compute_residual(V_mag, V_ang, Ybus, S)

                self.samples.append({"P": S.real,
                                     "Q": S.imag,
                                     "G": Ybus.real.flatten(),
                                     "B": Ybus.imag.flatten(),
                                     "V_init": v_ill,
                                     "theta_init": theta_ill,
                                     "iterations":it,
                                     "V_pred": V_mag,
                                     "Phi_pred": V_ang,
                                     "resd_real": resd.real,
                                     "resd_imag": resd.imag,
                            })

            except pp.powerflow.LoadflowNotConverged:
                print(f"Sample {_}: Ill-conditioned case did not converge!")
        
        with open( "data.pkl", "wb") as f:
            pickle.dump(self.samples, f)


 
    def __len__(self):
        return len(self.samples)
 
    def __getitem__(self, idx):
        sample = self.samples[idx]
        return {
            'input': torch.FloatTensor(sample['input']),
            'output': torch.FloatTensor(sample['output'])
        }
    
V_ext = 1.2  # External voltage in pu
P = 0.1  # Active power in MW
Q = 0.05  # Reactive power in MVar
G = 100  # Short-circuit power in MVA
B = 0.1  # Short-circuit impedance
V_init = [1.02, 1.0]  # Initial voltages in pu
theta_init = [0, 0]  # Initial angles in degrees

# create network object
Net = SimpleTwoBus(V_ext,P,Q,G,B,V_init,theta_init)
net = Net.net

# generate data
PF_data = PowerFlowDataset(net, num_samples=10, max_iteration=50, tolerance_mva=1e-5, v_perturb=0.15, theta_perturb=30)

def create_grid_dataset(grid_num=100):
    VM_PU_RANGE = [0.9, 1.1]  #
    P_MW_RANGE = [0.0, 0.2]  #
    Q_MVAR_RANGE = [0.0, 0.1]  #
    G_RANGE = [80, 120]  #
    B_RANGE = [0.01, 0.2]  #
    INIT_VM_PU_MIN = 0.9  #
    INIT_VM_PU_MAX = 1.1  #
    INIT_THETA_MAX = -1
    INIT_THETA_MIN = 1

    flattened_data = []
    for _ in tqdm(range(grid_num)):
        V_ext = np.random.uniform(VM_PU_RANGE[0], VM_PU_RANGE[1])
        P = np.random.uniform(P_MW_RANGE[0], P_MW_RANGE[1])
        Q = np.random.uniform(Q_MVAR_RANGE[0], Q_MVAR_RANGE[1])
        G = np.random.uniform(G_RANGE[0], G_RANGE[1])  # Short-circuit power in MVA
        B = np.random.uniform(B_RANGE[0], B_RANGE[1])  # Short-circuit impedance

        V_init = [
            np.random.uniform(INIT_VM_PU_MIN, INIT_VM_PU_MAX),
            np.random.uniform(INIT_VM_PU_MIN, INIT_VM_PU_MAX),
        ]
        theta_init = [
            np.random.uniform(INIT_THETA_MIN, INIT_THETA_MAX),
            np.random.uniform(INIT_THETA_MIN, INIT_THETA_MAX),
        ]

        Net = SimpleTwoBus(V_ext,P,Q,G,B,V_init,theta_init)
        net = Net.net
        PF_data = PowerFlowDataset(net, num_samples=10, max_iteration=50, tolerance_mva=1e-5, v_perturb=0.15, theta_perturb=30)
        for d in PF_data.samples:
            X = np.concatenate([d['P'], d['Q'], d['G'], d['B'], d['V_init'], d['theta_init'], d['V_pred'], d['Phi_pred'], d['resd_real'], d['resd_imag']])
            Y = d['iterations']
            flattened_data.append(np.append(X, Y))
    return flattened_data

flattened_data = create_grid_dataset(100)
# Convert to NumPy array
data_array = np.array(flattened_data)
# Display shape of the array
print(data_array.shape)
np.save('vector_data.npy', data_array)