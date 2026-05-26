import numpy as np
from typing import Optional, Union
from dataclasses import dataclass

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem, Descriptors, MACCSkeys
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


SMILES_CHARS = [
    " ", "#", "%", "(", ")", "+", "-", ".", "/",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "=", "@", "A", "B", "C", "F", "H", "I", "K", "L", "M",
    "N", "O", "P", "R", "S", "T", "U", "V", "W", "X", "Y",
    "Z", "[", "\\", "]", "a", "b", "c", "d", "e", "f", "g",
    "h", "i", "l", "m", "n", "o", "p", "r", "s", "t", "u",
    "v", "w", "x", "y", "z", "~",
]
CHAR_TO_IDX = {c: i + 1 for i, c in enumerate(SMILES_CHARS)}
CHAR_TO_IDX["<PAD>"] = 0
CHAR_TO_IDX["<START>"] = len(SMILES_CHARS) + 1
CHAR_TO_IDX["<END>"] = len(SMILES_CHARS) + 2
IDX_TO_CHAR = {v: k for k, v in CHAR_TO_IDX.items()}
SMILES_VOCAB_SIZE = len(CHAR_TO_IDX)


@dataclass
class FingerprintConfig:
    radius: int = 2
    n_bits: int = 2048
    use_chirality: bool = True
    use_features: bool = False


def validate_smiles(smiles: str) -> bool:
    if not RDKIT_AVAILABLE:
        return bool(smiles and len(smiles) > 0)
    mol = Chem.MolFromSmiles(smiles)
    return mol is not None


def standardize_smiles(smiles: str) -> Optional[str]:
    if not RDKIT_AVAILABLE:
        return smiles
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    except Exception:
        return None


def mol_from_smiles(smiles: str):
    if not RDKIT_AVAILABLE:
        return None
    try:
        return Chem.MolFromSmiles(smiles)
    except Exception:
        return None


def morgan_fingerprint(
    smiles: str,
    config: Optional[FingerprintConfig] = None,
) -> Optional[np.ndarray]:
    if not RDKIT_AVAILABLE:
        return None
    cfg = config or FingerprintConfig()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(
        mol, cfg.radius, nBits=cfg.n_bits,
        useChirality=cfg.use_chirality, useFeatures=cfg.use_features,
    )
    arr = np.zeros((cfg.n_bits,), dtype=np.float32)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def maccs_fingerprint(smiles: str) -> Optional[np.ndarray]:
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = MACCSkeys.GenMACCSKeys(mol)
    arr = np.zeros((fp.GetNumBits(),), dtype=np.float32)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def rdkit_fingerprint(smiles: str) -> Optional[np.ndarray]:
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = Chem.RDKFingerprint(mol)
    arr = np.zeros((fp.GetNumBits(),), dtype=np.float32)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def compute_all_fingerprints(smiles: str) -> dict:
    return {
        "morgan": morgan_fingerprint(smiles),
        "maccs": maccs_fingerprint(smiles),
        "rdkit": rdkit_fingerprint(smiles),
    }


def compute_descriptors(smiles: str) -> Optional[dict]:
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Descriptors.MolLogP(mol),
        "hba": Descriptors.NumHAcceptors(mol),
        "hbd": Descriptors.NumHDonors(mol),
        "tpsa": Descriptors.TPSA(mol),
        "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        "ring_count": Descriptors.RingCount(mol),
        "aromatic_rings": Descriptors.NumAromaticRings(mol),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
    }


def tanimoto_similarity(fp1: np.ndarray, fp2: np.ndarray) -> float:
    intersection = np.sum(fp1 & fp2)
    union = np.sum(fp1 | fp2)
    if union == 0:
        return 0.0
    return float(intersection / union)


def batch_tanimoto_matrix(fps: list[np.ndarray]) -> np.ndarray:
    n = len(fps)
    mat = np.ones((n, n), dtype=np.float32)
    for i in range(n):
        for j in range(i + 1, n):
            sim = tanimoto_similarity(fps[i], fps[j])
            mat[i, j] = sim
            mat[j, i] = sim
    return mat


def smiles_to_onehot(smiles: str, max_len: int = 128) -> np.ndarray:
    tokens = ["<START>"] + list(smiles) + ["<END>"]
    seq = np.zeros((max_len, SMILES_VOCAB_SIZE), dtype=np.float32)
    for i, token in enumerate(tokens):
        if i >= max_len:
            break
        idx = CHAR_TO_IDX.get(token, CHAR_TO_IDX[" "])
        seq[i, idx] = 1.0
    return seq


def smiles_to_indices(smiles: str, max_len: int = 128) -> np.ndarray:
    tokens = ["<START>"] + list(smiles) + ["<END>"]
    indices = np.zeros(max_len, dtype=np.int64)
    for i, token in enumerate(tokens):
        if i >= max_len:
            break
        indices[i] = CHAR_TO_IDX.get(token, CHAR_TO_IDX[" "])
    return indices


def indices_to_smiles(indices: Union[np.ndarray, list[int]]) -> str:
    chars = []
    for idx in indices:
        idx = int(idx)
        if idx == 0:
            continue
        c = IDX_TO_CHAR.get(idx, "")
        if c == "<START>":
            continue
        if c == "<END>":
            break
        chars.append(c)
    return "".join(chars)


def filter_valid_smiles(smiles_list: list[str]) -> list[str]:
    valid = []
    for s in smiles_list:
        vs = standardize_smiles(s)
        if vs:
            valid.append(vs)
    return valid
