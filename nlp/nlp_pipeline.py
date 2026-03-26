import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
import os
import datetime
from dateutil import parser as dateparser

# Attempt to download NLTK data silently (works offline if already cached)
for _pkg in ['stopwords', 'wordnet', 'omw-1.4']:
    try:
        nltk.download(_pkg, quiet=True)
    except Exception:
        pass  # No internet – use whatever is already installed

try:
    stop_words = set(stopwords.words('english'))
except LookupError:
    stop_words = set()  # fallback: no stopword filtering

try:
    lemmatizer = WordNetLemmatizer()
except LookupError:
    lemmatizer = None  # fallback: no lemmatization


def _lemmatize(word: str) -> str:
    global lemmatizer
    if lemmatizer is None:
        return word
    try:
        return lemmatizer.lemmatize(word)
    except Exception:
        lemmatizer = None
        return word

# ─────────────────────────────────────────────
# Predefined skill keywords for extraction
# ─────────────────────────────────────────────
SKILL_KEYWORDS = {
    # ==================== PROGRAMMING LANGUAGES ====================
    # General Purpose
    "python", "java", "javascript", "typescript", "c++", "c", "c#", "go", "golang", "rust", 
    "ruby", "php", "swift", "kotlin", "scala", "dart", "perl", "haskell", "elixir", "erlang",
    "clojure", "lisp", "scheme", "f#", "ocaml", "groovy", "lua", "r", "matlab", "julia",
    "fortran", "cobol", "pascal", "delphi", "ada", "verilog", "vhdl", "assembly", "arm",
    "bash", "zsh", "shell", "powershell", "cmd", "vim script", "emacs lisp",
    
    # Web Technologies
    "html", "html5", "css", "css3", "sass", "scss", "less", "tailwind", "bootstrap",
    "javascript", "typescript", "jsx", "tsx", "webassembly", "wasm", "json", "xml", "yaml",
    
    # Mobile Development
    "swift", "kotlin", "java android", "objective-c", "react native", "flutter", "xamarin",
    "ionic", "cordova", "native script", "swiftui", "jetpack compose",
    
    # Database Languages
    "sql", "pl/sql", "t-sql", "mysql", "postgresql", "mongodb query", "graphql",
    "nosql", "cassandra cql", "redis commands",
    
    # ==================== FRAMEWORKS & LIBRARIES ====================
    # Backend Frameworks
    "django", "flask", "fastapi", "pyramid", "tornado", "spring", "spring boot", 
    "spring cloud", "hibernate", "jakarta ee", "express.js", "nestjs", "next.js", 
    "nuxt.js", "ruby on rails", "sinatra", "laravel", "symfony", "codeigniter",
    "asp.net", ".net core", "asp.net core", "gin", "echo", "fiber", "actix",
    
    # Frontend Frameworks
    "react", "react.js", "vue", "vue.js", "angular", "angular.js", "svelte", "ember.js",
    "backbone.js", "jquery", "alpine.js", "htmx", "lit", "solid.js", "qwik", 
    "next.js", "gatsby", "remix", "astro",
    
    # Mobile Frameworks
    "react native", "flutter", "xamarin", "ionic", "capacitor", "cordova", "native script",
    "swiftui", "jetpack compose", "kotlin multiplatform",
    
    # Game Development
    "unity", "unreal engine", "godot", "cryengine", "cocos2d", "spritekit", "scenekit",
    
    # ==================== MACHINE LEARNING & AI ====================
    # ML Frameworks
    "tensorflow", "tensorflow.js", "pytorch", "keras", "scikit-learn", "sklearn", 
    "xgboost", "lightgbm", "catboost", "jax", "theano", "caffe", "mxnet", "onnx",
    
    # Deep Learning
    "deep learning", "neural networks", "cnn", "convolutional neural networks", 
    "rnn", "recurrent neural networks", "lstm", "transformer", "attention mechanism",
    "gan", "generative adversarial networks", "vae", "autoencoder", "reinforcement learning",
    
    # NLP
    "nlp", "natural language processing", "huggingface", "transformers", "bert", "gpt",
    "llama", "falcon", "gemini", "claude", "mistral", "langchain", "llamaindex",
    "spacy", "nltk", "stanford nlp", "word2vec", "glove", "sentiment analysis",
    "named entity recognition", "text classification", "machine translation",
    
    # Computer Vision
    "computer vision", "opencv", "yolo", "detectron", "image segmentation", 
    "object detection", "image classification", "facial recognition", "ocr",
    "tesseract", "easyocr", "pytesseract",
    
    # ML Operations
    "mlops", "mlflow", "kubeflow", "vertex ai", "sagemaker", "databricks ml",
    "model deployment", "model serving", "feature store",
    
    # Data Science
    "data science", "data analysis", "data mining", "statistics", "hypothesis testing",
    "a/b testing", "experimentation", "predictive modeling", "time series analysis",
    "forecasting", "clustering", "classification", "regression", "dimensionality reduction",
    
    # ==================== DATA & ANALYTICS ====================
    # Data Manipulation
    "pandas", "numpy", "scipy", "dask", "polars", "vaex", "modin", "cuDF",
    
    # Visualization
    "matplotlib", "seaborn", "plotly", "dash", "bokeh", "altair", "ggplot2",
    "tableau", "power bi", "powerbi", "looker", "looker studio", "qlik", 
    "metabase", "superset", "grafana", "kibana",
    
    # Big Data
    "big data", "hadoop", "hdfs", "spark", "pyspark", "spark sql", "spark streaming",
    "flink", "kafka", "kafka streams", "pulsar", "storm", "hive", "hbase",
    "cassandra", "mongodb", "elasticsearch", "opensearch",
    
    # Data Engineering
    "data engineering", "etl", "elt", "data pipeline", "data warehouse", "data lake",
    "data lakehouse", "snowflake", "databricks", "bigquery", "redshift", "synapse",
    "dbt", "dataform", "airflow", "prefect", "dagster", "luigi", "stich", "fivetran",
    
    # Databases
    "mysql", "postgresql", "postgres", "sqlite", "oracle", "sql server", "mariadb",
    "mongodb", "cassandra", "dynamodb", "cosmos db", "firestore", "rethinkdb",
    "redis", "memcached", "elasticsearch", "opensearch", "neo4j", "arangodb",
    "timescaledb", "influxdb", "prometheus", "clickhouse", "snowflake", "bigquery",
    
    # ==================== CLOUD & DEVOPS ====================
    # Cloud Providers
    "aws", "amazon web services", "ec2", "s3", "lambda", "rds", "dynamodb",
    "azure", "microsoft azure", "gcp", "google cloud", "oracle cloud", "oci",
    "ibm cloud", "digitalocean", "linode", "vultr", "heroku", "netlify", "vercel",
    
    # Cloud Services
    "serverless", "cloud functions", "fargate", "eks", "aks", "gke", "ecs",
    "cloudfront", "cloudflare", "fastly", "api gateway", "load balancer",
    
    # Container & Orchestration
    "docker", "kubernetes", "k8s", "openshift", "rancher", "podman", "containerd",
    "helm", "istio", "linkerd", "consul", "nomad",
    
    # CI/CD
    "ci/cd", "jenkins", "gitlab ci", "github actions", "circleci", "travis ci",
    "teamcity", "bamboo", "argo cd", "flux", "spinnaker",
    
    # Infrastructure as Code
    "terraform", "terragrunt", "pulumi", "cloudformation", "cdk", "ansible",
    "chef", "puppet", "saltstack", "crossplane",
    
    # Monitoring & Observability
    "prometheus", "grafana", "datadog", "new relic", "dynatrace", "appdynamics",
    "elk stack", "elastic stack", "splunk", "loki", "tempo", "jaeger", "zipkin",
    
    # Version Control
    "git", "github", "gitlab", "bitbucket", "svn", "mercurial", "perforce",
    
    # Operating Systems
    "linux", "ubuntu", "centos", "redhat", "debian", "alpine", "unix", "windows server",
    "macos", "ios", "android",
    
    # ==================== WEB DEVELOPMENT ====================
    # APIs
    "rest api", "restful", "graphql", "grpc", "websocket", "soap", "odata",
    "openapi", "swagger", "postman", "api design", "api development",
    
    # Web Servers
    "nginx", "apache", "caddy", "traefik", "iis", "tomcat", "jetty", "undertow",
    
    # Web Security
    "oauth", "oauth2", "jwt", "saml", "openid connect", "cors", "csrf", "xss",
    "sql injection", "authentication", "authorization", "ssl", "tls", "https",
    
    # ==================== SOFTWARE ENGINEERING ====================
    # Methodologies
    "agile", "scrum", "kanban", "lean", "waterfall", "saFe", "xp", "extreme programming",
    "tdd", "test driven development", "bdd", "behavior driven development", "ddd",
    "domain driven design", "microservices", "monolith", "soa", "event driven",
    
    # Testing
    "unit testing", "integration testing", "e2e testing", "performance testing",
    "load testing", "stress testing", "security testing", "automated testing",
    "jest", "pytest", "unittest", "junit", "testng", "selenium", "cypress",
    "playwright", "puppeteer", "k6", "jmeter", "gatling", "locust",
    
    # Architecture & Design
    "system design", "software architecture", "design patterns", "solid principles",
    "clean code", "refactoring", "code review", "technical documentation",
    
    # ==================== SECURITY ====================
    "cybersecurity", "information security", "network security", "application security",
    "cloud security", "devsecops", "penetration testing", "vulnerability assessment",
    "cryptography", "encryption", "pki", "certificates", "firewall", "ids", "ips",
    "siem", "soar", "zero trust", "iam", "pam", "mfa", "rbac", "soc",
    
    # ==================== HR & TALENT MANAGEMENT ====================
    # Core HR
    "recruitment", "talent acquisition", "sourcing", "headhunting", "executive search",
    "hr", "human resources", "hrbp", "hr business partner", "people operations",
    "employee relations", "employee engagement", "employee experience",
    
    # HR Operations
    "payroll", "benefits administration", "compensation", "total rewards",
    "hr compliance", "labor law", "employment law", "fmla", "ada", "eeoc",
    "hris", "workday", "sap successfactors", "oracle hcm", "bambooHR",
    "adp", "paychex", "zenefits", "rippling",
    
    # Talent Management
    "performance management", "performance review", "okr", "kpi", "goal setting",
    "talent management", "succession planning", "career development",
    "training", "learning & development", "onboarding", "offboarding",
    
    # Recruitment Tools
    "applicant tracking systems", "ats", "greenhouse", "lever", "workable",
    "recruiter", "linkedin recruiter", "boolean search", "x-ray search",
    
    # Diversity
    "diversity & inclusion", "dei", "diversity hiring", "inclusive recruitment",
    
    # ==================== PROJECT MANAGEMENT ====================
    "project management", "program management", "product management", "agile project management",
    "scrum master", "product owner", "jira", "confluence", "asana", "trello",
    "monday.com", "clickup", "notion", "smartsheet", "microsoft project",
    "risk management", "stakeholder management", "budget management", "resource management",
    
    # ==================== SOFT SKILLS ====================
    "communication", "written communication", "verbal communication", "presentation",
    "leadership", "team leadership", "technical leadership", "people management",
    "teamwork", "collaboration", "cross-functional collaboration", "mentoring",
    "coaching", "problem solving", "critical thinking", "analytical skills",
    "time management", "organization", "prioritization", "adaptability", "flexibility",
    "creativity", "innovation", "negotiation", "conflict resolution", "decision making",
    "emotional intelligence", "empathy", "customer service", "customer success",
    
    # ==================== BUSINESS & DOMAIN ====================
    # Business
    "business analysis", "business intelligence", "requirements gathering",
    "stakeholder management", "vendor management", "strategic planning",
    
    # Sales & Marketing
    "sales", "business development", "account management", "crm", "salesforce",
    "marketing", "digital marketing", "seo", "sem", "content marketing",
    "social media", "email marketing", "growth hacking",
    
    # Finance
    "finance", "accounting", "financial analysis", "budgeting", "forecasting",
    "fp&a", "financial modeling", "investment", "trading", "fintech",
    
    # Healthcare
    "healthcare", "hippa", "ehr", "electronic health records", "clinical research",
    
    # Legal
    "legal", "compliance", "regulatory", "gdpr", "ccpa", "sox", "audit",
    
    # ==================== EMERGING TECHNOLOGIES ====================
    "blockchain", "web3", "ethereum", "smart contracts", "solidity", "crypto",
    "nft", "defi", "metaverse", "ar", "augmented reality", "vr", "virtual reality",
    "mr", "mixed reality", "iot", "internet of things", "edge computing",
    "quantum computing", "robotics", "automation", "rpa", "robotic process automation",
    
    # ==================== CERTIFICATIONS ====================
    "aws certified", "azure certified", "gcp certified", "ckad", "cks", "cka",
    "pmp", "capm", "prince2", "csm", "psm", "safe", "itil",
    "cissp", "cism", "cisa", "security+", "ceh", "oscp",
    "scrum master", "product owner", "lean six sigma", "six sigma",
}


def clean_text(text: str) -> str:
    """Full NLP cleaning: lowercase → remove special chars → tokenize → stopword removal → lemmatize."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    words = text.split()
    words = [
        _lemmatize(word)
        for word in words
        if word not in stop_words and len(word) > 1
    ]
    return " ".join(words)


def extract_section(text: str, section_name: str) -> str:
    """
    Extract a named section from resume text.
    Looks for section_name header, returns text until next header.
    """
    if not isinstance(text, str):
        return ""
    # Common section boundary markers
    pattern = rf'(?i){re.escape(section_name)}[\s\S]*?(?=\n[A-Z][A-Z\s]{{3,}}:|$)'
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return ""


def extract_experience_section(text: str) -> str:
    """Return only the Experience section of a resume."""
    section = extract_section(text, "Experience")
    if not section:
        section = extract_section(text, "Work Experience")
    if not section:
        section = extract_section(text, "Work History")
    if not section:
        section = extract_section(text, "Professional Experience")
    return section if section else text  # fall back to full text


def extract_skills(text: str) -> list:
    """Extract skills from text by matching against SKILL_KEYWORDS."""
    if not isinstance(text, str):
        return []
    # Replace newlines with spaces and pad string
    text_lower = " " + text.lower().replace('\n', ' ') + " "
    found = []
    
    for skill in SKILL_KEYWORDS:
        # Use negative lookbehind and lookahead for letters/numbers to match exact words,
        # which correctly handles skills ending in non-word chars like C++
        pattern = r'(?<![a-z0-9])' + re.escape(skill) + r'(?![a-z0-9])'
        if re.search(pattern, text_lower):
            found.append(skill)
            
    return sorted(set(found))


def extract_education(text: str) -> str:
    """Return only the Education section of a resume."""
    section = extract_section(text, "Education")
    if not section:
        section = extract_section(text, "Education and Training")
    return section


def count_skills(text: str) -> int:
    """Return the number of identified skills in a text."""
    return len(extract_skills(text))


def extract_experience(text: str) -> float:
    """
    Extract years of experience scoped to the Experience section only.
    Strategy 1: Direct mention "X+ years"
    Strategy 2: Sum date ranges within the Experience section.
    """
    if not isinstance(text, str):
        return 0.0

    exp_text = extract_experience_section(text).lower()
    current_date = datetime.datetime.now()

    match = re.search(r'(\d+)\+?\s+year', exp_text)
    if match:
        years = float(match.group(1))
        if 0 < years < 50:
            return years

    total_days = 0
    date_ranges = re.findall(
        r'(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|\d{1,2}/\d{4}|\d{4})'
        r'\s*(?:to|-)\s*'
        r'(current|present|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|\d{1,2}/\d{4}|\d{4})',
        exp_text, re.IGNORECASE
    )

    for start_str, end_str in date_ranges:
        try:
            start_date = dateparser.parse(start_str.strip(), fuzzy=True)
            if 'current' in end_str.lower() or 'present' in end_str.lower():
                end_date = current_date
            else:
                end_date = dateparser.parse(end_str.strip(), fuzzy=True)
            diff = (end_date - start_date).days
            if 30 < diff < 365 * 45:
                total_days += diff
        except Exception:
            continue

    return round(total_days / 365, 1)


class NLPPipeline:
    """
    Enhanced NLP Pipeline for processing resume text.
    Includes skill extraction, experience calculation, TF-IDF, and n-grams.
    """

    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.tfidf_vectorizer = None

    def preprocess_text(self, text):
        """
        Basic text preprocessing: lowercase, remove special characters.
        """
        # Convert to lowercase
        text = text.lower()
        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def tokenize_and_clean(self, text):
        """
        Tokenize, remove stopwords, and lemmatize using NLTK (spaCy fallback removed).
        """
        # Use NLTK tokenization
        tokens = nltk.word_tokenize(text)

        # Remove stopwords and lemmatize
        cleaned_tokens = []
        for token in tokens:
            if token.lower() not in self.stop_words and token.isalpha():
                lemma = _lemmatize(token.lower())
                cleaned_tokens.append(lemma)

        return cleaned_tokens

    def tokenize_and_clean_nltk(self, text):
        """
        Alternative using NLTK for tokenization and lemmatization.
        """
        # Tokenize
        tokens = nltk.word_tokenize(text)

        # Remove stopwords and lemmatize
        cleaned_tokens = []
        for token in tokens:
            if token.lower() not in self.stop_words and token.isalpha():
                lemma = self.lemmatizer.lemmatize(token.lower())
                cleaned_tokens.append(lemma)

        return cleaned_tokens

    def extract_ngrams(self, tokens, n=2):
        """
        Extract n-grams from tokens.
        """
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i+n])
            ngrams.append(ngram)
        return ngrams

    def process_resume_text(self, text, use_spacy=True, include_ngrams=True):
        """
        Complete NLP processing for a single resume.
        """
        # Preprocess
        cleaned_text = self.preprocess_text(text)

        # Tokenize and clean
        if use_spacy:
            tokens = self.tokenize_and_clean(cleaned_text)
        else:
            tokens = self.tokenize_and_clean_nltk(cleaned_text)

        # Extract n-grams if requested
        features = {
            'tokens': tokens,
            'token_count': len(tokens),
            'unique_tokens': len(set(tokens))
        }

        if include_ngrams:
            bigrams = self.extract_ngrams(tokens, 2)
            trigrams = self.extract_ngrams(tokens, 3)
            features['bigrams'] = bigrams
            features['trigrams'] = trigrams

        return features

    def fit_tfidf(self, texts, max_features=1000, ngram_range=(1, 2)):
        """
        Fit TF-IDF vectorizer on a corpus of texts.
        """
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words='english',
            lowercase=True
        )
        self.tfidf_vectorizer.fit(texts)
        print(f"TF-IDF fitted with {len(self.tfidf_vectorizer.get_feature_names_out())} features")

    def transform_tfidf(self, texts):
        """
        Transform texts to TF-IDF vectors.
        """
        if self.tfidf_vectorizer is None:
            raise ValueError("TF-IDF vectorizer not fitted. Call fit_tfidf first.")
        return self.tfidf_vectorizer.transform(texts)

    def get_tfidf_features(self, text):
        """
        Get TF-IDF features for a single text.
        """
        if self.tfidf_vectorizer is None:
            raise ValueError("TF-IDF vectorizer not fitted.")
        vector = self.tfidf_vectorizer.transform([text])
        return vector.toarray().flatten()

    def extract_resume_features(self, text):
        """
        Extract comprehensive features from resume text.
        """
        features = {}

        # Basic text features
        features['cleaned_text'] = clean_text(text)
        features['skills'] = extract_skills(text)
        features['skill_count'] = len(features['skills'])
        features['experience_years'] = extract_experience(text)
        features['education_section'] = extract_education(text)
        features['experience_section'] = extract_experience_section(text)

        # Token-level features
        tokens = self.tokenize_and_clean_nltk(features['cleaned_text'])
        features['tokens'] = tokens
        features['token_count'] = len(tokens)
        features['unique_tokens'] = len(set(tokens))

        return features


def process_dataset_nlp(df, text_column='Resume_str'):
    """
    Apply enhanced NLP pipeline to the entire dataset.
    """
    nlp_pipeline = NLPPipeline()

    # Process each resume
    processed_features = []
    for text in df[text_column]:
        features = nlp_pipeline.extract_resume_features(text)
        processed_features.append(features)

    # Convert to DataFrame
    features_df = pd.DataFrame(processed_features)

    # Fit TF-IDF on all texts
    nlp_pipeline.fit_tfidf(df[text_column].tolist())

    # Add TF-IDF vectors (as list for now, can be expanded later)
    tfidf_vectors = []
    for text in df[text_column]:
        vector = nlp_pipeline.get_tfidf_features(text)
        tfidf_vectors.append(vector)

    features_df['tfidf_vector'] = tfidf_vectors

    return features_df, nlp_pipeline


# Example usage
if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    John Doe
    Software Engineer

    Experience:
    Senior Python Developer at Tech Corp (Jan 2020 - Present)
    - Developed ML models using TensorFlow and scikit-learn
    - Built REST APIs with Flask and FastAPI
    - Managed databases with PostgreSQL and MongoDB

    Junior Developer at Startup Inc (Jun 2018 - Dec 2019)
    - Worked with JavaScript, React, and Node.js
    - Implemented CI/CD pipelines with Jenkins

    Skills:
    Python, JavaScript, SQL, Machine Learning, Docker, AWS

    Education:
    BS Computer Science, University of Tech (2014-2018)
    """

    pipeline = NLPPipeline()
    features = pipeline.extract_resume_features(sample_text)

    print("Enhanced NLP Processing:")
    print(f"Skills found: {features['skills']}")
    print(f"Experience years: {features['experience_years']}")
    print(f"Skill count: {features['skill_count']}")
    print(f"Token count: {features['token_count']}")