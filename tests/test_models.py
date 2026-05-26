import numpy as np
import torch

from src.models import (
    CancerClassifier, CancerClassifierConfig,
    Trainer, TrainingConfig,
    Predictor,
    MoleculeVAE, MoleculeVAEConfig,
    DTIPredictor, DTIPredictorConfig,
    DrugDiscoveryPipeline,
    DrugBankIntegrator, DrugBankConfig,
    FingerprintConfig,
    validate_smiles, standardize_smiles,
    smiles_to_indices, indices_to_smiles,
    morgan_fingerprint, compute_descriptors,
    tanimoto_similarity,
)
from src.models.treatment_recommender import (
    TreatmentRecommender, TreatmentRecommenderConfig,
    lookup_drug_knowledge, list_available_cancers,
    CANCER_DRUG_DB,
)
from src.models.drug_response import DrugResponsePredictor, DrugResponseConfig


class TestCancerClassifier:

    def test_config_defaults(self):
        cfg = CancerClassifierConfig()
        assert cfg.input_dim == 20500
        assert cfg.num_cancer_types == 3
        assert cfg.num_subtypes == 6
        assert cfg.num_stages == 4

    def test_forward_shape(self, classifier):
        x = torch.randn(2, 100)
        out = classifier(x)
        assert "cancer_type" in out
        assert "subtype" in out
        assert "stage" in out
        assert out["cancer_type"].shape == (2, 3)
        assert out["subtype"].shape == (2, 6)
        assert out["stage"].shape == (2, 4)

    def test_predict_proba(self, classifier):
        x = torch.randn(3, 100)
        probs = classifier.predict_proba(x)
        for key in ["cancer_type", "subtype", "stage"]:
            assert probs[key].shape[0] == 3
            assert torch.allclose(probs[key].sum(dim=1), torch.ones(3))

    def test_predict(self, classifier):
        x = torch.randn(2, 100)
        preds = classifier.predict(x)
        for key in ["cancer_type", "subtype", "stage"]:
            assert preds[key].shape == (2,)

    def test_small_config(self):
        cfg = CancerClassifierConfig(input_dim=10, hidden_dims=(8, 4), use_batch_norm=False)
        model = CancerClassifier(cfg)
        x = torch.randn(1, 10)
        out = model(x)
        assert out["cancer_type"].shape == (1, 3)

    def test_batch_norm(self):
        cfg_with = CancerClassifierConfig(input_dim=10, hidden_dims=(8,), use_batch_norm=True)
        cfg_without = CancerClassifierConfig(input_dim=10, hidden_dims=(8,), use_batch_norm=False)
        m1 = CancerClassifier(cfg_with)
        m2 = CancerClassifier(cfg_without)
        x = torch.randn(4, 10)
        o1 = m1(x)
        o2 = m2(x)
        assert o1["cancer_type"].shape == o2["cancer_type"].shape


class TestTrainer:

    def test_training_config_defaults(self):
        cfg = TrainingConfig()
        assert cfg.batch_size == 64
        assert cfg.learning_rate == 1e-3
        assert cfg.num_epochs == 100

    def test_train_epoch(self, classifier, training_config, sample_batch):
        from torch.utils.data import DataLoader, Dataset
        X, yc, ys, yst = sample_batch
        class DictDataset(Dataset):
            def __init__(self, X, yc, ys, yst):
                self.X = torch.tensor(X, dtype=torch.float32)
                self.yc = torch.tensor(yc, dtype=torch.long)
                self.ys = torch.tensor(ys, dtype=torch.long)
                self.yst = torch.tensor(yst, dtype=torch.long)
            def __len__(self):
                return len(self.X)
            def __getitem__(self, i):
                return {"input": self.X[i], "cancer_type": self.yc[i], "subtype": self.ys[i], "stage": self.yst[i]}
        dataset = DictDataset(X, yc, ys, yst)
        loader = DataLoader(dataset, batch_size=2)
        trainer = Trainer(classifier, training_config)
        loss = trainer._train_epoch(loader)
        assert isinstance(loss, float)
        assert loss > 0

    def test_validate(self, classifier, training_config, sample_batch):
        from torch.utils.data import DataLoader, Dataset
        X, yc, ys, yst = sample_batch
        class DictDataset(Dataset):
            def __init__(self, X, yc, ys, yst):
                self.X = torch.tensor(X, dtype=torch.float32)
                self.yc = torch.tensor(yc, dtype=torch.long)
                self.ys = torch.tensor(ys, dtype=torch.long)
                self.yst = torch.tensor(yst, dtype=torch.long)
            def __len__(self):
                return len(self.X)
            def __getitem__(self, i):
                return {"input": self.X[i], "cancer_type": self.yc[i], "subtype": self.ys[i], "stage": self.yst[i]}
        dataset = DictDataset(X, yc, ys, yst)
        loader = DataLoader(dataset, batch_size=2)
        trainer = Trainer(classifier, training_config)
        loss, metrics = trainer._validate(loader)
        assert isinstance(loss, float)
        assert "cancer_type" in metrics
        assert "accuracy" in metrics["cancer_type"]


class TestPredictor:

    def test_cancer_type_names(self):
        from src.models.predict import CANCER_TYPE_NAMES
        assert "肺癌" in CANCER_TYPE_NAMES
        assert "乳腺癌" in CANCER_TYPE_NAMES

    def test_predict_single_sample(self, classifier):
        x = np.random.randn(100).astype(np.float32)
        config = classifier.config
        model = CancerClassifier(config)
        model.load_state_dict(classifier.state_dict())
        model.eval()
        import torch
        with torch.no_grad():
            probs = model.predict_proba(torch.tensor(x.reshape(1, -1)))
            preds = model.predict(torch.tensor(x.reshape(1, -1)))
        assert preds["cancer_type"].shape == (1,)


class TestMoleculeVAE:

    def test_config_defaults(self):
        cfg = MoleculeVAEConfig()
        assert cfg.latent_dim == 128
        assert cfg.max_seq_len == 128

    def test_vae_forward(self):
        from src.models.molecule_utils import SMILES_VOCAB_SIZE
        cfg = MoleculeVAEConfig(
            vocab_size=SMILES_VOCAB_SIZE,
            char_embed_dim=16,
            encoder_hidden=32,
            latent_dim=16,
            decoder_hidden=32,
            max_seq_len=16,
            use_bidirectional=False,
        )
        vae = MoleculeVAE(cfg)
        x = torch.randint(1, SMILES_VOCAB_SIZE, (2, 16))
        recon, mu, logvar = vae(x)
        assert recon.shape == (2, 16, SMILES_VOCAB_SIZE)
        assert mu.shape == (2, 16)
        assert logvar.shape == (2, 16)

    def test_vae_loss(self):
        from src.models.molecule_utils import SMILES_VOCAB_SIZE
        cfg = MoleculeVAEConfig(
            vocab_size=SMILES_VOCAB_SIZE,
            char_embed_dim=16,
            encoder_hidden=32,
            latent_dim=16,
            decoder_hidden=32,
            max_seq_len=16,
        )
        vae = MoleculeVAE(cfg)
        x = torch.randint(1, SMILES_VOCAB_SIZE, (2, 16))
        recon, mu, logvar = vae(x)
        loss_dict = vae.loss(x, recon, mu, logvar)
        assert "loss" in loss_dict
        assert "recon_loss" in loss_dict
        assert "kl_loss" in loss_dict
        assert loss_dict["loss"].item() > 0

    def test_reparameterize(self):
        cfg = MoleculeVAEConfig(latent_dim=16)
        vae = MoleculeVAE(cfg)
        mu = torch.randn(3, 16)
        logvar = torch.randn(3, 16)
        z = vae.reparameterize(mu, logvar)
        assert z.shape == (3, 16)


class TestDTIPredictor:

    def test_config_defaults(self):
        cfg = DTIPredictorConfig()
        assert cfg.drug_fingerprint_dim == 2048
        assert cfg.target_embed_dim == 128

    def test_forward(self):
        cfg = DTIPredictorConfig(drug_fingerprint_dim=64, target_embed_dim=16, hidden_dims=(32, 16))
        model = DTIPredictor(cfg)
        fp = torch.randn(2, 64)
        tgt = torch.randn(2, 16)
        out = model(fp, tgt)
        assert out.shape == (2,)
        assert torch.all(out >= 0) and torch.all(out <= 1)

    def test_predict_interaction(self):
        cfg = DTIPredictorConfig(drug_fingerprint_dim=64, target_embed_dim=16, hidden_dims=(32, 16))
        model = DTIPredictor(cfg)
        fp = np.random.randn(64).astype(np.float32)
        tgt = np.random.randn(16).astype(np.float32)
        prob = model.predict_interaction(fp, tgt)
        assert prob.shape == (1,)
        assert 0 <= prob[0] <= 1


class TestDrugDiscoveryPipeline:

    def test_pipeline_init(self):
        from src.models.molecule_utils import SMILES_VOCAB_SIZE
        vae_cfg = MoleculeVAEConfig(
            vocab_size=SMILES_VOCAB_SIZE,
            char_embed_dim=16, encoder_hidden=32,
            latent_dim=16, decoder_hidden=32, max_seq_len=16,
        )
        dti_cfg = DTIPredictorConfig(
            drug_fingerprint_dim=64, target_embed_dim=16, hidden_dims=(32, 16),
        )
        vae = MoleculeVAE(vae_cfg)
        dti = DTIPredictor(dti_cfg)
        pipe = DrugDiscoveryPipeline(vae=vae, dti=dti)
        assert pipe.vae is vae
        assert pipe.dti is dti

    def test_screen_empty_library(self):
        pipe = DrugDiscoveryPipeline()
        tgt = np.random.randn(16).astype(np.float32)
        result = pipe.screen_virtual_library([], tgt, top_k=5)
        assert result == []


class TestDrugBankIntegrator:

    def test_load_builtin(self):
        integrator = DrugBankIntegrator()
        integrator.load_builtin()
        stats = integrator.get_statistics()
        assert stats["num_drugs"] > 0
        assert stats["num_targets"] > 0

    def test_known_drugs(self):
        integrator = DrugBankIntegrator()
        drugs = integrator.known_drugs
        assert "DB00398" in drugs
        assert drugs["DB00398"]["name"] == "Sorafenib"

    def test_search_by_name(self):
        integrator = DrugBankIntegrator()
        integrator.load_builtin()
        results = integrator.search_drugs_by_name("sorafenib")
        assert len(results) > 0
        assert results[0]["name"] == "Sorafenib"

    def test_search_by_target(self):
        integrator = DrugBankIntegrator()
        integrator.load_builtin()
        results = integrator.search_drugs_by_target("EGFR")
        assert len(results) > 0

    def test_cancer_relevant_targets(self):
        integrator = DrugBankIntegrator()
        assert "EGFR" in integrator.cancer_targets
        assert "BRAF" in integrator.cancer_targets

    def test_dti_pairs_filter(self):
        integrator = DrugBankIntegrator()
        integrator.load_builtin()
        all_pairs = integrator.get_dti_pairs(cancer_relevant_only=False)
        cancer_pairs = integrator.get_dti_pairs(cancer_relevant_only=True)
        assert len(all_pairs) > 0
        assert len(cancer_pairs) <= len(all_pairs)

    def test_dti_matrix(self):
        integrator = DrugBankIntegrator()
        integrator.load_builtin()
        matrix = integrator.build_dti_matrix()
        assert matrix.ndim == 2
        assert matrix.shape[0] > 0

    def test_drug_fingerprints(self):
        integrator = DrugBankIntegrator()
        integrator.load_builtin()
        fps = integrator.compute_drug_fingerprints()
        assert isinstance(fps, dict)
        for k, v in fps.items():
            assert isinstance(v, np.ndarray)

    def test_drug_descriptors(self):
        integrator = DrugBankIntegrator()
        integrator.load_builtin()
        descs = integrator.compute_drug_descriptors()
        for k, v in descs.items():
            assert "mw" in v


class TestMoleculeUtils:

    def test_smiles_vocab(self):
        from src.models.molecule_utils import SMILES_VOCAB_SIZE, CHAR_TO_IDX, IDX_TO_CHAR
        assert SMILES_VOCAB_SIZE > 0
        assert CHAR_TO_IDX["<PAD>"] == 0
        assert IDX_TO_CHAR[0] == "<PAD>"

    def test_validate_smiles(self):
        assert validate_smiles("CCO") is True
        assert validate_smiles("") is False

    def test_smiles_to_indices_roundtrip(self):
        smi = "CCO"
        indices = smiles_to_indices(smi, max_len=20)
        assert indices[0] > 0
        recovered = indices_to_smiles(indices)
        assert recovered == smi

    def test_indices_to_smiles_empty(self):
        assert indices_to_smiles([]) == ""

    def test_tanimoto_identical(self):
        fp = np.array([1, 0, 1, 0, 1, 0], dtype=np.float32)
        sim = tanimoto_similarity(fp, fp)
        assert sim == 1.0

    def test_tanimoto_zero(self):
        fp1 = np.array([1, 0, 0], dtype=np.float32)
        fp2 = np.array([0, 1, 1], dtype=np.float32)
        sim = tanimoto_similarity(fp1, fp2)
        assert sim == 0.0

    def test_tanimoto_no_union(self):
        fp = np.zeros(5, dtype=np.float32)
        sim = tanimoto_similarity(fp, fp)
        assert sim == 0.0


class TestTreatmentRecommender:

    def test_config_defaults(self):
        cfg = TreatmentRecommenderConfig()
        assert cfg.input_dim == 20500
        assert cfg.top_k == 5

    def test_forward_shape(self):
        cfg = TreatmentRecommenderConfig(input_dim=20, clinical_dim=5,
                                         hidden_dims=(16, 8), num_drug_classes=10)
        model = TreatmentRecommender(cfg)
        gene = torch.randn(2, 20)
        clin = torch.randn(2, 5)
        out = model(gene, clin)
        assert out.shape == (2, 10)

    def test_recommend(self):
        cfg = TreatmentRecommenderConfig(input_dim=20, clinical_dim=5,
                                         hidden_dims=(16, 8), num_drug_classes=64,
                                         use_batch_norm=False)
        model = TreatmentRecommender(cfg)
        gene = torch.randn(1, 20)
        clin = torch.randn(1, 5)
        recs = model.recommend(gene, clin, "肺癌", top_k=3)
        assert len(recs) <= 3
        assert recs[0]["drug_name"] is not None

    def test_recommend_unknown_cancer(self):
        cfg = TreatmentRecommenderConfig(input_dim=20, clinical_dim=5,
                                         hidden_dims=(16, 8), num_drug_classes=64,
                                         use_batch_norm=False)
        model = TreatmentRecommender(cfg)
        gene = torch.randn(1, 20)
        clin = torch.randn(1, 5)
        recs = model.recommend(gene, clin, "UNKNOWN", top_k=3)
        assert recs == []

    def test_lookup_drug_knowledge(self):
        drugs = lookup_drug_knowledge("肺癌")
        assert len(drugs) > 0
        assert any(d["category"] == "標靶" for d in drugs)

    def test_lookup_by_category(self):
        drugs = lookup_drug_knowledge("肺癌", category="免疫")
        assert all(d["category"] == "免疫" for d in drugs)

    def test_lookup_unknown_cancer(self):
        assert lookup_drug_knowledge("UNKNOWN") == []

    def test_list_cancers(self):
        cancers = list_available_cancers()
        assert "肺癌" in cancers

    def test_drug_db_structure(self):
        for cancer, categories in CANCER_DRUG_DB.items():
            for cat, drugs in categories.items():
                for d in drugs:
                    assert "name" in d
                    assert "avg_response" in d
                    assert 0 <= d["avg_response"] <= 1


class TestDrugResponsePredictor:

    def test_config_defaults(self):
        cfg = DrugResponseConfig()
        assert cfg.gene_input_dim == 20500
        assert cfg.drug_vocab_size == 100

    def test_forward_shape(self):
        cfg = DrugResponseConfig(gene_input_dim=20, drug_vocab_size=10,
                                 drug_embed_dim=4, hidden_dims=(16, 8))
        model = DrugResponsePredictor(cfg)
        gene = torch.randn(2, 20)
        drug = torch.randint(0, 10, (2,))
        out = model(gene, drug)
        assert out.shape == (2,)
        assert torch.all(out >= 0) and torch.all(out <= 1)

    def test_rank_drugs(self):
        cfg = DrugResponseConfig(gene_input_dim=20, drug_vocab_size=10,
                                 drug_embed_dim=4, hidden_dims=(16, 8))
        model = DrugResponsePredictor(cfg)
        gene = np.random.randn(20).astype(np.float32)
        ranked = model.rank_drugs(gene, [0, 1, 2])
        assert len(ranked) == 3
        assert ranked[0]["rank"] == 1
        assert ranked[2]["rank"] == 3


class TestFingerprintConfig:

    def test_defaults(self):
        cfg = FingerprintConfig()
        assert cfg.radius == 2
        assert cfg.n_bits == 2048
