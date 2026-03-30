import os
from dataclasses import dataclass
from typing import Optional, Tuple

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from nlp.experience_extractor import extract_experience_years, extract_required_experience_years
from nlp.skill_extractor import SkillExtractor
from nlp.preprocessing import clamp01


@dataclass(frozen=True)
class MatchScoreComponents:
    semantic: float
    skills: float
    experience: float


class MatchingEngine:
    """
    Deterministic hybrid matching:
      score = 0.5 * semantic + 0.3 * skills + 0.2 * experience

    semantic: TF-IDF cosine similarity in [0,1]
    skills: Jaccard similarity in [0,1]
    experience: similarity based on closeness to required years in [0,1]
    """

    def __init__(self, tfidf_vectorizer, skill_extractor: Optional[SkillExtractor] = None):
        self.tfidf_vectorizer = tfidf_vectorizer
        self.skill_extractor = skill_extractor or SkillExtractor()

    @classmethod
    def from_artifacts(cls, model_dir: str):
        tfidf_path = os.path.join(model_dir, "tfidf_vectorizer.pkl")
        if not os.path.exists(tfidf_path):
            raise FileNotFoundError(f"Missing tfidf vectorizer artifact: {tfidf_path}")
        tfidf = joblib.load(tfidf_path)
        return cls(tfidf_vectorizer=tfidf)

    def semantic_similarity(self, resume_text: str, job_description: str) -> float:
        if self.tfidf_vectorizer is None:
            return 0.0
        vectors = self.tfidf_vectorizer.transform([resume_text, job_description])
        sim = float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])
        return clamp01(sim)

    def skills_similarity(self, resume_text: str, job_description: str) -> float:
        r_skills = set(self.skill_extractor.extract_skills(resume_text))
        j_skills = set(self.skill_extractor.extract_skills(job_description))

        if not r_skills and not j_skills:
            return 0.5  # neutral when nothing is extractable
        if not r_skills or not j_skills:
            return 0.0

        inter = len(r_skills & j_skills)
        union = len(r_skills | j_skills)
        if union == 0:
            return 0.0
        return clamp01(inter / union)

    def experience_similarity(self, resume_text: str, job_description: str) -> float:
        cand_years, _cand_conf = extract_experience_years(resume_text)
        req_years = extract_required_experience_years(job_description)

        if cand_years is None or req_years is None or req_years <= 0:
            return 0.5  # neutral

        diff = abs(float(cand_years) - float(req_years))
        score = 1.0 - (diff / float(req_years))
        return clamp01(score)

    def score_candidate(self, resume_text: str, job_description: str) -> Tuple[float, MatchScoreComponents]:
        semantic = self.semantic_similarity(resume_text, job_description)
        skills = self.skills_similarity(resume_text, job_description)
        experience = self.experience_similarity(resume_text, job_description)

        score = (0.5 * semantic) + (0.3 * skills) + (0.2 * experience)
        score = clamp01(score)

        return score, MatchScoreComponents(semantic=semantic, skills=skills, experience=experience)

    def score_candidate_percent(self, resume_text: str, job_description: str) -> int:
        score, _components = self.score_candidate(resume_text, job_description)
        return int(round(score * 100.0))

