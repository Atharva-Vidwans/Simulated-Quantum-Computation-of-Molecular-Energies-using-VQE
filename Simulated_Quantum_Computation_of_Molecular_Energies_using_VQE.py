import sys
import pennylane as qml
import numpy as np


def variational_ansatz(params, wires):
    """

    This is a custom ansatz. It applies alternating layers of rotations and CNOTs.

    Args:
        params (np.ndarray): An array of floating-point numbers with size (n, 3),
            where n is the number of parameter sets required (this is determined by
            the problem Hamiltonian).
        wires (qml.Wires): The device wires this circuit will run on.
    """
    n_qubits = len(wires)
    n_rotations = len(params)

    if n_rotations > 1:
        n_layers = n_rotations // n_qubits
        n_extra_rots = n_rotations - n_layers * n_qubits

        # Alternating layers of unitary rotations on every qubit followed by a
        # ring cascade of CNOTs.
        for layer_idx in range(n_layers):
            layer_params = params[layer_idx * n_qubits : layer_idx * n_qubits + n_qubits, :]
            qml.broadcast(qml.Rot, wires, pattern="single", parameters=layer_params)
            qml.broadcast(qml.CNOT, wires, pattern="ring")

        extra_params = params[-n_extra_rots:, :]
        extra_wires = wires[: n_qubits - 1 - n_extra_rots : -1]
        qml.broadcast(qml.Rot, extra_wires, pattern="single", parameters=extra_params)
    else:
        # For 1-qubit case, just a single rotation to the qubit
        qml.Rot(*params[0], wires=wires[0])
    

def run_vqe(H):
    """This function runs the variational quantum eigensolver on the problem Hamiltonian using the
    variational ansatz specified above.
    
    Args:
        H (qml.Hamiltonian): The input Hamiltonian

    Returns:
        The ground state energy of the Hamiltonian.
    """
    # Initialize parameters
    num_qubits = len(H.wires)
    num_param_sets = (2 ** num_qubits) - 1
    params = np.random.uniform(low=-np.pi / 2, high=np.pi / 2, size=(num_param_sets, 3))

    energy = 0
    
    # Create a quantum device, set up a cost funtion and optimizer, and run the VQE.
    dev = qml.device("default.qubit",wires=num_qubits)

    qnodes= qml.QNode(variational_ansatz,dev)
    
    cost_fn = qml.ExpvalCost(variational_ansatz, H, dev)

    opt = qml.AdamOptimizer(stepsize=0.1)

    max_iterations = 200
    conv_tol = 1e-06

    for n in range(max_iterations):
        params, prev_energy = opt.step_and_cost(cost_fn, params)
        energy = cost_fn(params)
        if n%10 ==0 :
            print(" Energy for iteration "+str(n)+" : "+str(energy))
        
    # Return the ground state energy
    return energy


def pauli_token_to_operator(token):
    """
    Helper function to turn strings into qml operators.

    Args:
        token (str): A Pauli operator input in string form.

    Returns:
        A qml.Operator instance of the Pauli.
    """
    qubit_terms = []

    for term in token:
        # Special case of identity
        if term == "I":
            qubit_terms.append(qml.Identity(0))
        else:
            pauli, qubit_idx = term[0], term[1:]
            if pauli == "X":
                qubit_terms.append(qml.PauliX(int(qubit_idx)))
            elif pauli == "Y":
                qubit_terms.append(qml.PauliY(int(qubit_idx)))
            elif pauli == "Z":
                qubit_terms.append(qml.PauliZ(int(qubit_idx)))
            else:
                print("Invalid input.")

    full_term = qubit_terms[0]
    for term in qubit_terms[1:]:
        full_term = full_term @ term

    return full_term


def parse_hamiltonian_input(input_data):
    """
    Turns the input contents into a Hamiltonian.

    Args:
        filename(str): Name of the input file that contains the Hamiltonian.

    Returns:
        qml.Hamiltonian object of the Hamiltonian specified in the file.
    """
    # Get the input
    coeffs = []
    pauli_terms = []

    # Go through line by line and build up the Hamiltonian
    for line in input_data.split("S"):
        line = line.strip()
        tokens = line.split(" ")

        # Parse coefficients
        sign, value = tokens[0], tokens[1]

        coeff = float(value)
        if sign == "-":
            coeff *= -1
        coeffs.append(coeff)

        # Parse Pauli component
        pauli = tokens[2:]
        pauli_terms.append(pauli_token_to_operator(pauli))

    return qml.Hamiltonian(coeffs, pauli_terms)


if __name__ == "__main__":
    # Turn input to Hamiltonian
    H = parse_hamiltonian_input(sys.stdin.read())
    
    # Send Hamiltonian through VQE routine and output the solution
    ground_state_energy = run_vqe(H)
    print(" Ground state Energy of given Hamiltonian is : ",f"{ground_state_energy:.6f}")
