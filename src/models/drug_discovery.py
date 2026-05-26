import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import Optional, Union

from .molecule_utils import (
    SMILES_VOCAB_SIZE, CHAR_TO_IDX, IDX_TO_CHAR,
    smiles_to_indices, indices_to_smiles, validate_smiles,
    standardize_smiles, morgan_fingerprint, FingerprintConfig,
)


@dataclass
class MoleculeVAEConfig:
    vocab_size: int = SMILES_VOCAB_SIZE
    char_embed_dim: int = 128
    encoder_hidden: int = 256
    encoder_layers: int = 2
    latent_dim: int = 128
    decoder_hidden: int = 256
    decoder_layers: int = 2
    max_seq_len: int = 128
    dropout: float = 0.2
    kl_weight: float = 0.1
    use_bidirectional: bool = True


@dataclass
class DTIPredictorConfig:
    drug_fingerprint_dim: int = 2048
    target_embed_dim: int = 128
    target_vocab_size: int = 64
    hidden_dims: tuple = (1024, 512, 256)
    dropout: float = 0.3
    use_batch_norm: bool = True
    fp_config: FingerprintConfig = field(default_factory=FingerprintConfig)


class EncoderRNN(nn.Module):

    def __init__(self, config: MoleculeVAEConfig):
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(config.vocab_size, config.char_embed_dim, padding_idx=0)
        self.rnn = nn.GRU(
            config.char_embed_dim,
            config.encoder_hidden,
            num_layers=config.encoder_layers,
            batch_first=True,
            bidirectional=config.use_bidirectional,
            dropout=config.dropout if config.encoder_layers > 1 else 0,
        )
        rnn_out_dim = config.encoder_hidden * (2 if config.use_bidirectional else 1)
        self.mu = nn.Linear(rnn_out_dim, config.latent_dim)
        self.logvar = nn.Linear(rnn_out_dim, config.latent_dim)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        lengths = (x != 0).sum(dim=1).clamp(min=1).cpu()
        emb = self.embedding(x)
        packed = nn.utils.rnn.pack_padded_sequence(emb, lengths, batch_first=True, enforce_sorted=False)
        _, h = self.rnn(packed)
        if self.config.use_bidirectional:
            h = h.view(self.config.encoder_layers, 2, -1, self.config.encoder_hidden)
            h = torch.cat([h[:, 0], h[:, 1]], dim=-1)
        h = h[-1]
        return self.mu(h), self.logvar(h)


class DecoderRNN(nn.Module):

    def __init__(self, config: MoleculeVAEConfig):
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(config.vocab_size, config.char_embed_dim, padding_idx=0)
        self.rnn = nn.GRU(
            config.char_embed_dim,
            config.decoder_hidden,
            num_layers=config.decoder_layers,
            batch_first=True,
            dropout=config.dropout if config.decoder_layers > 1 else 0,
        )
        self.latent_proj = nn.Linear(config.latent_dim, config.decoder_hidden)
        self.out = nn.Linear(config.decoder_hidden, config.vocab_size)

    def forward(
        self,
        z: torch.Tensor,
        target: Optional[torch.Tensor] = None,
        teacher_forcing_ratio: float = 0.5,
    ) -> torch.Tensor:
        batch_size = z.size(0)
        max_len = self.config.max_seq_len if target is None else target.size(1)
        h = self.latent_proj(z).unsqueeze(0).repeat(self.config.decoder_layers, 1, 1)

        start_idx = CHAR_TO_IDX["<START>"]
        input_tokens = torch.full((batch_size, 1), start_idx, dtype=torch.long, device=z.device)
        outputs = torch.zeros(batch_size, max_len, self.config.vocab_size, device=z.device)

        for t in range(max_len):
            emb = self.embedding(input_tokens)
            out, h = self.rnn(emb, h)
            logits = self.out(out.squeeze(1))
            outputs[:, t, :] = logits

            if target is not None and np.random.random() < teacher_forcing_ratio:
                input_tokens = target[:, t].unsqueeze(1)
            else:
                pred = logits.argmax(dim=1)
                input_tokens = pred.unsqueeze(1)

        return outputs


class MoleculeVAE(nn.Module):

    def __init__(self, config: Optional[MoleculeVAEConfig] = None):
        super().__init__()
        self.config = config or MoleculeVAEConfig()
        self.encoder = EncoderRNN(self.config)
        self.decoder = DecoderRNN(self.config)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(
        self,
        x: torch.Tensor,
        teacher_forcing_ratio: float = 0.5,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        recon = self.decoder(z, target=x, teacher_forcing_ratio=teacher_forcing_ratio)
        return recon, mu, logvar

    def loss(
        self,
        x: torch.Tensor,
        recon: torch.Tensor,
        mu: torch.Tensor,
        logvar: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        recon_loss = F.cross_entropy(
            recon.reshape(-1, self.config.vocab_size),
            x.reshape(-1),
            ignore_index=0,
            reduction="mean",
        )
        kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
        total = recon_loss + self.config.kl_weight * kl_loss
        return {"loss": total, "recon_loss": recon_loss, "kl_loss": kl_loss}

    @torch.no_grad()
    def generate(self, num_molecules: int = 10, max_len: Optional[int] = None) -> list[str]:
        self.eval()
        max_seq = max_len or self.config.max_seq_len
        device = next(self.parameters()).device
        z = torch.randn(num_molecules, self.config.latent_dim, device=device)
        h = self.decoder.latent_proj(z).unsqueeze(0).repeat(self.config.decoder_layers, 1, 1)

        start_idx = CHAR_TO_IDX["<START>"]
        input_tokens = torch.full((num_molecules, 1), start_idx, dtype=torch.long, device=device)
        smiles_list = [[] for _ in range(num_molecules)]
        done = [False] * num_molecules

        for _ in range(max_seq):
            emb = self.decoder.embedding(input_tokens)
            out, h = self.decoder.rnn(emb, h)
            logits = self.decoder.out(out.squeeze(1))
            probs = F.softmax(logits, dim=1)
            pred = torch.multinomial(probs, 1).squeeze(1)

            for i in range(num_molecules):
                if done[i]:
                    continue
                c = IDX_TO_CHAR.get(int(pred[i].item()), "")
                if c == "<END>":
                    done[i] = True
                elif c not in ("<PAD>", "<START>"):
                    smiles_list[i].append(c)

            if all(done):
                break
            input_tokens = pred.unsqueeze(1)

        return [standardize_smiles("".join(s)) or "".join(s) for s in smiles_list]

    @torch.no_grad()
    def encode_smiles(self, smiles: str) -> Optional[np.ndarray]:
        self.eval()
        indices = smiles_to_indices(smiles, self.config.max_seq_len)
        x = torch.tensor(indices, dtype=torch.long).unsqueeze(0)
        device = next(self.parameters()).device
        x = x.to(device)
        mu, logvar = self.encoder(x)
        return mu.cpu().numpy().squeeze(0)

    @torch.no_grad()
    def decode_latent(self, z: np.ndarray) -> str:
        self.eval()
        z_t = torch.tensor(z, dtype=torch.float32).unsqueeze(0)
        device = next(self.parameters()).device
        z_t = z_t.to(device)
        h = self.decoder.latent_proj(z_t).unsqueeze(0).repeat(self.config.decoder_layers, 1, 1)
        start_idx = CHAR_TO_IDX["<START>"]
        inp = torch.full((1, 1), start_idx, dtype=torch.long, device=device)
        chars = []
        for _ in range(self.config.max_seq_len):
            emb = self.decoder.embedding(inp)
            out, h = self.decoder.rnn(emb, h)
            logits = self.decoder.out(out.squeeze(1))
            pred = logits.argmax(dim=1).item()
            c = IDX_TO_CHAR.get(pred, "")
            if c == "<END>":
                break
            if c not in ("<PAD>", "<START>"):
                chars.append(c)
            inp = torch.tensor([[pred]], dtype=torch.long, device=device)
        return standardize_smiles("".join(chars)) or "".join(chars)


class DTIPredictor(nn.Module):

    def __init__(self, config: Optional[DTIPredictorConfig] = None):
        super().__init__()
        self.config = config if config is not None else DTIPredictorConfig()

        layers = []
        prev = self.config.drug_fingerprint_dim + self.config.target_embed_dim
        for h in self.config.hidden_dims:
            layers.append(nn.Linear(prev, h))
            if self.config.use_batch_norm:
                layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(self.config.dropout))
            prev = h
        self.fusion = nn.Sequential(*layers)
        self.classifier = nn.Linear(prev, 1)

    def forward(
        self,
        drug_fp: torch.Tensor,
        target_emb: torch.Tensor,
    ) -> torch.Tensor:
        x = torch.cat([drug_fp, target_emb], dim=1)
        features = self.fusion(x)
        return torch.sigmoid(self.classifier(features)).squeeze(-1)

    @torch.no_grad()
    def predict_interaction(
        self,
        drug_fp: Union[np.ndarray, torch.Tensor],
        target_emb: Union[np.ndarray, torch.Tensor],
    ) -> np.ndarray:
        if isinstance(drug_fp, np.ndarray):
            drug_fp = torch.tensor(drug_fp, dtype=torch.float32)
        if isinstance(target_emb, np.ndarray):
            target_emb = torch.tensor(target_emb, dtype=torch.float32)
        if drug_fp.ndim == 1:
            drug_fp = drug_fp.unsqueeze(0)
        if target_emb.ndim == 1:
            target_emb = target_emb.unsqueeze(0)

        self.eval()
        probs = self.forward(drug_fp, target_emb)
        return probs.cpu().numpy()

    @torch.no_grad()
    def predict_from_smiles(
        self,
        smiles_list: list[str],
        target_emb: Union[np.ndarray, torch.Tensor],
        fp_config: Optional[FingerprintConfig] = None,
    ) -> list[dict]:
        cfg = fp_config or self.config.fp_config
        if isinstance(target_emb, np.ndarray):
            target_emb = torch.tensor(target_emb, dtype=torch.float32)
        if target_emb.ndim == 1:
            target_emb = target_emb.unsqueeze(0)
        target_emb = target_emb.expand(len(smiles_list), -1)

        fps = []
        valid_idx = []
        for i, smi in enumerate(smiles_list):
            fp = morgan_fingerprint(smi, cfg)
            if fp is not None:
                fps.append(fp)
                valid_idx.append(i)

        if not fps:
            return []

        fp_t = torch.tensor(np.stack(fps), dtype=torch.float32)
        te_t = target_emb[:len(fps)]

        probs = self.forward(fp_t, te_t).cpu().numpy()
        return [
            {"smiles": smiles_list[valid_idx[i]], "interaction_probability": round(float(p), 4)}
            for i, p in enumerate(probs)
        ]


# ---- End-to-end drug discovery pipeline ----

class DrugDiscoveryPipeline:

    def __init__(
        self,
        vae: Optional[MoleculeVAE] = None,
        dti: Optional[DTIPredictor] = None,
    ):
        self.vae = vae or MoleculeVAE()
        self.dti = dti or DTIPredictor()

    def discover_candidate_drugs(
        self,
        target_emb: Union[np.ndarray, torch.Tensor],
        num_candidates: int = 100,
        top_k: int = 10,
    ) -> list[dict]:
        generated = self.vae.generate(num_molecules=num_candidates)
        valid_smiles = [s for s in generated if validate_smiles(s)]
        if not valid_smiles:
            return []

        predictions = self.dti.predict_from_smiles(valid_smiles, target_emb)
        predictions.sort(key=lambda x: x["interaction_probability"], reverse=True)
        for rank, item in enumerate(predictions[:top_k], 1):
            item["rank"] = rank
        return predictions[:top_k]

    def screen_virtual_library(
        self,
        smiles_library: list[str],
        target_emb: Union[np.ndarray, torch.Tensor],
        top_k: int = 20,
    ) -> list[dict]:
        results = self.dti.predict_from_smiles(smiles_library, target_emb)
        results.sort(key=lambda x: x["interaction_probability"], reverse=True)
        for rank, item in enumerate(results[:top_k], 1):
            item["rank"] = rank
        return results[:top_k]
