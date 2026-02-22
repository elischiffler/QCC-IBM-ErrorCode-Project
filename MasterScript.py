# pip install qiskit qiskit-ibm-runtime qiskit-experiments matplotlib pylatexenc

# Step 2: Log in to IBM Quantum
from qiskit_ibm_runtime import QiskitRuntimeService

# PASTE YOUR API TOKEN BELOW inside the quotes
MY_API_TOKEN = "PASTE_YOUR_IBM_QUANTUM_TOKEN_HERE"

# Save the account to disk (only needs to be done once per session)
try:
    QiskitRuntimeService.save_account(channel="ibm_quantum_platform", token=MY_API_TOKEN, overwrite=True)
    service = QiskitRuntimeService()
    print("Successfully logged in!")
except Exception as e:
    print(f"Login failed: {e}")

# list all backends
backends = service.backends(simulator=False, operational=True)

print("Here are the machines you can use:")
print("-" * 30)
for b in backends:
    print(f"Name: {b.name}")

# Step 3: Choose a Quantum Computer

BACKEND_NAME = "ibm_torino"  # <--- CHANGE THIS NAME
QUBIT_TO_TEST = [0]         # We are testing Qubit 0

print(f"Target Locked: {BACKEND_NAME}")
print(f"For Qubit: {QUBIT_TO_TEST}")

# Step 4: Run Randomized Benchmarking
from qiskit_experiments.library import StandardRB
from qiskit_experiments.framework import ParallelExperiment
import matplotlib.pyplot as plt

# 1. Get the backend
try:
    backend = service.backend(BACKEND_NAME)
    print(f"Connected to {BACKEND_NAME}.")
except:
    print(f"Could not find backend '{BACKEND_NAME}'.")
    raise

# 2. Configure the Experiment
# We run sequences of random gates of increasing length to see how fast the qubit errors out.
lengths = [1, 10, 20, 30, 40, 50, 60, 70, 80, 100]
num_samples = 10  # Run 10 different random patterns for accuracy
seed = 101        # Fixed seed for reproducibility

# Create the Randomized Benchmarking (RB) experiment
exp = StandardRB(
    physical_qubits=QUBIT_TO_TEST,
    lengths=lengths,
    num_samples=num_samples,
    seed=seed
)

print("Job submitted to the Quantum Computer! Waiting for results...")

# 3. Run and Analyze
exp_data = exp.run(backend)
exp_data.block_for_results()  # This pauses the code until the job is done

# 4. Display Results
print("\n" + "="*40)
print("RESULTS ACQUIRED")
print("="*40)

# Extract the Error Per Clifford (EPC)
# This is the "Score" needed for the Google Sheet
result = exp_data.analysis_results("EPC")
epc_value = result.value.value
epc_error = result.value.stderr

print(f"EPC Score (Error Rate): {epc_value:.6f}")
print(f"± Uncertainty: {epc_error:.6f}")
print("="*40)
print("\nCOPY THE 'EPC SCORE' INTO THE CLUB SPREADSHEET!")

# 5. Show the Graph
display(exp_data.figure(0))