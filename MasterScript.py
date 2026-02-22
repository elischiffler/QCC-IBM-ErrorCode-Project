import os
import sys
import getpass
import csv
import random
import time
import schedule
from datetime import datetime
import matplotlib.pyplot as plt

# --- Qiskit Imports ---
from qiskit_ibm_runtime import QiskitRuntimeService, IBMRuntimeError
from qiskit_experiments.library import StandardRB

# Member Name Setup
MEMBER_NAME = os.getenv("QCC_MEMBER_NAME")
if not MEMBER_NAME:
    MEMBER_NAME = input("Enter your Name: ").strip()
    if not MEMBER_NAME: MEMBER_NAME = "Anonymous_Member"

# Default is REAL mode unless QCC_TEST_MODE is explicitly set to a truthy value.
TEST_MODE = os.getenv("QCC_TEST_MODE", "0").strip().lower() in ("1", "true", "yes", "y")

IBM_TOKEN = os.getenv("IBM_QUANTUM_TOKEN")
if not TEST_MODE and not IBM_TOKEN:
    IBM_TOKEN = getpass.getpass("Paste your IBM Quantum Token: ").strip()

# --- CONFIGURATION ---
CSV_FILENAME = "qcc_results.csv"
CSV_HEADERS = [
    "Date", "Time", "Member Name", "Backend Name", "Qubit Tested", 
    "EPC Score", "Uncertainty (±)", "Usage Time (m)", 
    "Usage Time (s)", "Pending Time (m)", "Pending Time (s)"
]

MAX_RUNS = 7
RUN_COUNT = 0

def save_to_csv(data_dict):
    file_exists = os.path.isfile(CSV_FILENAME)
    with open(CSV_FILENAME, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(data_dict)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Data logged to {CSV_FILENAME}")

def run_quantum_experiment():
    global RUN_COUNT
    RUN_COUNT += 1
    
    print(f"\n--- Run {RUN_COUNT}/{MAX_RUNS} Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    usage_m, usage_s = 0, 0
    pending_m, pending_s = 0, 0
    
    try:
        if not TEST_MODE:
            token = IBM_TOKEN or os.getenv("IBM_QUANTUM_TOKEN")
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
            
            print("Listing backends and queue depths:")
            candidates = []
            backend_stats = []
            
            for b in service.backends(simulator=False, operational=True):
                jobs = b.status().pending_jobs
                print(f" - {b.name}: {jobs} jobs")
                backend_stats.append((b, jobs))
                if jobs < 200:
                    candidates.append(b)
            
            backend = random.choice(candidates) if candidates else min(backend_stats, key=lambda x: x[1])[0]
            BACKEND_NAME = backend.name
            print(f"Selected backend: {BACKEND_NAME}")
            QUBIT_TO_TEST = [0]
        else:
            # --- NOISY TEST MODE (AER) ---
            from qiskit_aer import AerSimulator
            from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError
        
            noise_model = NoiseModel()
            p1q = 0.001 
            error_1q = depolarizing_error(p1q, 1)
            noise_model.add_all_qubit_quantum_error(error_1q, ['sx', 'x', 'rz'])
            p_ro = 0.02
            error_ro = ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]])
            noise_model.add_all_qubit_readout_error(error_ro)
            backend = AerSimulator(noise_model=noise_model)
        
            BACKEND_NAME = "simulated_noisy_backend"
            QUBIT_TO_TEST = [0]
            usage_s, pending_s = 15, 2

        # --- EXPERIMENT SUBMISSION ---
        lengths = [1, 10, 20, 30, 40, 50, 60, 70, 80, 100]
        exp = StandardRB(physical_qubits=QUBIT_TO_TEST, lengths=lengths, num_samples=10)
        
        try:
            print(f"Submitting job to {BACKEND_NAME}...")
            exp_data = exp.run(backend)
            exp_data.block_for_results()
        except Exception as e:
            # Check for common "out of time" keywords in the error message
            error_msg = str(e).lower()
            if "insufficient" in error_msg or "limit" in error_msg or "quota" in error_msg:
                print("\n[CRITICAL ERROR] You have run out of IBM Quantum minutes!")
                print(f"Details: {e}")
                print("Ending program to prevent unnecessary background waiting.")
                os._exit(1) # Immediate hard exit of the background process
            else:
                raise e # Re-raise if it's a different error (like connection)
        
        # --- TIMING ---
        if not TEST_MODE:
            try:
                job = service.job(exp_data.job_ids[0])
                metrics = job.metrics()
                u_total_s = metrics.get('usage', {}).get('seconds', 0)
                usage_m, usage_s = divmod(u_total_s, 60)
                
                ts = job.timestamps()
                created_at = ts.get('created')
                running_at = ts.get('running')
                
                if created_at and running_at:
                    p_total_s = (running_at - created_at).total_seconds()
                    pending_m, pending_s = divmod(int(p_total_s), 60)
            except Exception as e:
                print(f"Timing error: {e}")

        # --- RESULTS ---
        result = exp_data.analysis_results("EPC", dataframe=False)
        if isinstance(result, list): result = result[0]
        epc = result.value
        
        try:
            from uncertainties import nominal_value, std_dev
            epc_val, epc_err = float(nominal_value(epc)), float(std_dev(epc))
        except:
            epc_val, epc_err = float(epc), 0.0

        save_to_csv({
            "Date": datetime.now().strftime("%m/%d/%Y"),
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Member Name": MEMBER_NAME,
            "Backend Name": BACKEND_NAME,
            "Qubit Tested": str(QUBIT_TO_TEST),
            "EPC Score": f"{epc_val:.6f}",
            "Uncertainty (±)": f"{epc_err:.6f}",
            "Usage Time (m)": int(usage_m),
            "Usage Time (s)": int(usage_s),
            "Pending Time (m)": int(pending_m),
            "Pending Time (s)": int(pending_s)
        })
        
        fig = exp_data.figure(0).figure
        fig.savefig("latest_rb_plot.png")
        print(f"Run {RUN_COUNT} Complete.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # --- SCHEDULING ---
    if RUN_COUNT < MAX_RUNS:
        next_interval = random.randint(2, 6)
        print(f"Waiting {next_interval} hours until next run...")
        schedule.every(next_interval).hours.do(reschedule_job)
    else:
        print("\n[Target Reached] 7 iterations complete.")
        
    return schedule.CancelJob

def reschedule_job():
    return run_quantum_experiment()

if __name__ == "__main__":
    print(f"QCC Scheduler Started. (Limit: {MAX_RUNS} runs)")
    run_quantum_experiment()

    while RUN_COUNT < MAX_RUNS:
        schedule.run_pending()
        time.sleep(1800)
    
    print("Process Finished.")
    sys.exit(0)