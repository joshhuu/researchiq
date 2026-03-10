"""
topic_classifier.py
Classifies a research paper into academic domains using sentence-transformer
cosine similarity against a curated list of domain descriptor phrases.

No external API calls after the model is first downloaded/cached.
"""
import asyncio
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer, util

# ── Lazy singleton ─────────────────────────────────────────────────────────────
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# ── Domain knowledge base ──────────────────────────────────────────────────────
# Each entry: (domain, sub_domain, representative_description)
# Descriptions are deliberately keyword-dense so the embeddings cluster well.
DOMAIN_DESCRIPTORS: List[tuple] = [
    # Machine Learning
    ("Machine Learning", "Deep Learning",
     "neural networks deep learning backpropagation gradient descent training hidden layers"),
    ("Machine Learning", "Natural Language Processing",
     "natural language processing text classification tokenization language models transformers BERT GPT"),
    ("Machine Learning", "Computer Vision",
     "image recognition object detection convolutional neural networks image segmentation visual features"),
    ("Machine Learning", "Reinforcement Learning",
     "reinforcement learning reward policy agent environment Q-learning Markov decision process"),
    ("Machine Learning", "Generative Models",
     "generative adversarial networks GAN variational autoencoder diffusion models image generation"),
    ("Machine Learning", "Federated Learning",
     "federated learning distributed training privacy preserving decentralized model aggregation"),
    ("Machine Learning", "Graph Neural Networks",
     "graph neural networks node classification link prediction graph convolution knowledge graph"),
    ("Machine Learning", "Explainable AI",
     "explainability interpretability attention maps SHAP LIME model transparency trustworthy"),
    # Computer Science
    ("Computer Science", "Algorithms and Data Structures",
     "algorithm complexity data structure sorting graph search optimization dynamic programming"),
    ("Computer Science", "Distributed Systems",
     "distributed computing cloud computing consensus fault tolerance scalability microservices"),
    ("Computer Science", "Cybersecurity",
     "security encryption vulnerability intrusion detection authentication cryptography malware"),
    ("Computer Science", "Human-Computer Interaction",
     "user interface usability interaction design user experience HCI accessibility"),
    ("Computer Science", "Software Engineering",
     "software architecture code quality testing refactoring agile DevOps CI/CD"),
    ("Computer Science", "Databases",
     "relational database SQL NoSQL query optimization indexing transaction ACID"),
    # Bioinformatics & Life Sciences
    ("Bioinformatics", "Genomics",
     "gene expression DNA sequencing genome genomics CRISPR variant calling RNA-seq"),
    ("Bioinformatics", "Proteomics",
     "protein structure proteomics amino acid folding molecular dynamics simulation"),
    ("Bioinformatics", "Drug Discovery",
     "drug discovery molecular docking virtual screening pharmacology target binding"),
    # Medical / Healthcare
    ("Medical / Healthcare", "Clinical Studies",
     "clinical trial patient treatment diagnosis prognosis healthcare medical imaging radiology"),
    ("Medical / Healthcare", "Epidemiology",
     "epidemiology disease outbreak public health infection mortality incidence prevalence"),
    ("Medical / Healthcare", "Medical Imaging",
     "MRI CT scan X-ray ultrasound segmentation lesion detection radiological imaging"),
    # Physics & Engineering
    ("Physics", "Quantum Computing",
     "quantum computing qubit quantum circuit entanglement superposition quantum error correction"),
    ("Physics", "Astrophysics",
     "astrophysics galaxy black hole cosmology gravitational waves telescope spectroscopy"),
    ("Electrical Engineering", "Signal Processing",
     "signal processing Fourier transform filter sampling frequency spectrum noise"),
    ("Electrical Engineering", "Wireless Communications",
     "wireless channel MIMO OFDM beamforming 5G spectrum allocation antenna"),
    # Mathematics
    ("Mathematics", "Statistics",
     "statistical analysis probability regression hypothesis testing Bayesian inference"),
    ("Mathematics", "Optimization",
     "convex optimization linear programming gradient convergence Lagrangian solver"),
    # Environmental Science
    ("Environmental Science", "Climate Change",
     "climate change global warming carbon emissions renewable energy sustainability greenhouse"),
    ("Environmental Science", "Ecology",
     "ecology biodiversity habitat species conservation environmental impact"),
    # Social Sciences
    ("Social Sciences", "Economics",
     "economics market financial monetary policy GDP inflation macroeconomics"),
    ("Social Sciences", "Education",
     "education learning curriculum pedagogy student performance instructional technology"),
    ("Social Sciences", "Psychology",
     "cognitive psychology behavior experiment human perception decision making"),
    # Robotics & Autonomous Systems
    ("Robotics", "Autonomous Systems",
     "robot autonomous vehicle path planning sensor fusion control SLAM navigation"),
    ("Robotics", "Human-Robot Interaction",
     "human robot interaction collaborative robot teleoperation manipulation grasping"),
    # Information Retrieval
    ("Information Retrieval", "Recommendation Systems",
     "recommendation collaborative filtering user preference item embedding matrix factorization"),
    ("Information Retrieval", "Search & Ranking",
     "information retrieval indexing query search ranking document relevance"),
]

# Precomputed in-process once the model loads
_descriptor_embeddings = None
_descriptor_texts = [d[2] for d in DOMAIN_DESCRIPTORS]


def _get_descriptor_embeddings():
    global _descriptor_embeddings
    if _descriptor_embeddings is None:
        model = _get_model()
        _descriptor_embeddings = model.encode(_descriptor_texts, convert_to_tensor=True)
    return _descriptor_embeddings


# ── Core synchronous classification ───────────────────────────────────────────
def _classify_sync(text: str) -> List[Dict]:
    model = _get_model()
    text_emb = model.encode(text[:2500], convert_to_tensor=True)
    desc_embs = _get_descriptor_embeddings()

    similarities = util.cos_sim(text_emb, desc_embs)[0].cpu().numpy()

    top_indices = np.argsort(similarities)[::-1]
    results = []
    seen: set = set()

    for idx in top_indices:
        domain, sub_domain, _ = DOMAIN_DESCRIPTORS[idx]
        score = float(similarities[idx])
        if score < 0.15:
            break                       # remaining entries are below threshold
        key = f"{domain}|{sub_domain}"
        if key not in seen:
            seen.add(key)
            results.append({
                "domain": domain,
                "sub_domain": sub_domain,
                "confidence": round(score, 3),
            })
        if len(results) >= 3:
            break

    return results or [
        {"domain": "Interdisciplinary", "sub_domain": "General Research", "confidence": 0.3}
    ]


async def classify_topics(text: str) -> List[Dict]:
    """Async wrapper — runs classification in a thread pool to avoid blocking."""
    return await asyncio.to_thread(_classify_sync, text)
