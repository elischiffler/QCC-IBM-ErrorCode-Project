import os
import sys
import getpass
import csv
from datetime import datetime
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_experiments.library import StandardRB
import matplotlib.pyplot as plt

# --- CSV CONFIGURATION ---
CSV_FILENAME = "qcc_results.csv"
CSV_HEADERS = [
    "DateTime", "Member Name", "Backend Name", "Qubit Tested", 
    "EPC Score", "Uncertainty (±)", "Usage Time (m)", 
    "Usage Time (s)", "Pending Time (m)", "Pending Time (s)"
]

def save_to_csv(data_dict):
    file_exists = os.path.isfile(CSV_FILENAME)
    with open(CSV_FILENAME, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data_dict)
    print(f"\n[Data saved to {CSV_FILENAME}]")

MEMBER_NAME = getpass.getuser() 
TEST_MODE = os.getenv("QCC_TEST_MODE", "1").strip() not in ("0", "false", "False")

# Initialize timing variables
usage_m, usage_s = 0, 0
pending_m, pending_s = 0, 0

if not TEST_MODE:
    # --- REAL HARDWARE MODE ---
    token = os.getenv("IBM_QUANTUM_TOKEN")
    if not token:
        token = getpass.getpass("Paste your IBM Quantum token: ").strip()

    try:
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
        BACKEND_NAME = "ibm_kyoto"  # Change as needed
        backend = service.backend(BACKEND_NAME)
        QUBIT_TO_TEST = [0]
    except Exception as e:
        print(f"Login/Backend failed: {e}")
        sys.exit(1)
else:
    # --- NOISY TEST MODE (AER) ---
    print("TEST MODE: Simulating noisy hardware using Aer...")
    try:
        from qiskit_aer import AerSimulator
        from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError

        # Create a noise model so EPC is NOT zero
        noise_model = NoiseModel()
        
        # 1-qubit gate error (e.g., 0.1% error)
        p1q = 0.001 
        error_1q = depolarizing_error(p1q, 1)
        noise_model.add_all_qubit_quantum_error(error_1q, ['sx', 'x', 'rz'])
        
        # Readout error (e.g., 2% error)
        p_readout = 0.02
        error_ro = ReadoutError([[1 - p_readout, p_readout], [p_readout, 1 - p_readout]])
        noise_model.add_all_qubit_readout_error(error_ro)

        backend = AerSimulator(noise_model=noise_model)
        BACKEND_NAME = "simulated_noisy_backend"
        QUBIT_TO_TEST = [0]
        
        # Mock some usage times for the CSV
        usage_s = 15
        pending_s = 2
    except ImportError:
        print("Error: qiskit-aer not found. Run 'pip install qiskit-aer'")
        sys.exit(1)

# --- RUN EXPERIMENT ---
lengths = [1, 10, 20, 30, 40, 50, 60, 70, 80, 100]
num_samples = 10
exp = StandardRB(physical_qubits=QUBIT_TO_TEST, lengths=lengths, num_samples=num_samples)

print(f"Running RB on {BACKEND_NAME}...")
exp_data = exp.run(backend)
exp_data.block_for_results()

# --- EXTRACT TIMING DATA (IBM ONLY) ---
if not TEST_MODE:
    try:
        job = service.job(exp_data.job_ids[0])
        metrics = job.metrics()
        u_total_s = metrics.get('usage', {}).get('seconds', 0)
        usage_m, usage_s = divmod(u_total_s, 60)
        
        ts = job.timestamps()
        if ts.get('running') and ts.get('created'):
            p_total_s = (ts['running'] - ts['created']).total_seconds()
            pending_m, pending_s = divmod(int(p_total_s), 60)
    except Exception:
        pass

# --- EXTRACT RESULTS & SAVE ---
# Added dataframe=False to clear the DeprecationWarning
result = exp_data.analysis_results("EPC", dataframe=False)
if isinstance(result, list): result = result[0]
epc = result.value

try:
    from uncertainties import nominal_value, std_dev
    epc_val, epc_err = float(nominal_value(epc)), float(std_dev(epc))
except:
    epc_val, epc_err = float(epc), 0.0

log_entry = {
    "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "Member Name": MEMBER_NAME,
    "Backend Name": BACKEND_NAME,
    "Qubit Tested": str(QUBIT_TO_TEST),
    "EPC Score": f"{epc_val:.6f}",
    "Uncertainty (±)": f"{epc_err:.6f}",
    "Usage Time (m)": int(usage_m),
    "Usage Time (s)": int(usage_s),
    "Pending Time (m)": int(pending_m),
    "Pending Time (s)": int(pending_s)
}
save_to_csv(log_entry)

print(f"\nFINAL EPC SCORE: {epc_val:.6f} ± {epc_err:.6f}")

# --- UPDATED VISUALIZATION BLOCK ---
try:
    # Grab the actual figure object from the FigureData container
    fig_data = exp_data.figure(0)
    fig = fig_data.figure  # This accesses the underlying Matplotlib object
    
    # Check if we are in a headless environment or standard terminal
    if plt.get_backend().lower() == 'agg':
        fig.savefig("rb_results.png")
        print("\n[Plot saved as rb_results.png]")
    else:
        plt.show()
except Exception as e:
    print(f"\nCould not display plot: {e}")
    print("Check 'qcc_results.csv' for your data.")