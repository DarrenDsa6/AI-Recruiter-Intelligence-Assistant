JWT_TOKEN_TTL_SECONDS = 86400
JWT_ALGORITHM = "HS256"

RATE_LIMIT_MAX_MESSAGES = 50
RATE_LIMIT_WINDOW_SECONDS = 3600

MAX_MESSAGE_LENGTH = 2000

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10

WORKER_MAX_RETRIES = 3
WORKER_RETRY_DELAYS = [1, 2, 4]
WORKER_STREAM_NAME = "tailoring-jobs"
WORKER_STREAM_URGENT = "tailoring-jobs:urgent"
WORKER_STREAM_EMAIL = "tailoring-jobs:email"
WORKER_CONSUMER_GROUP = "tailoring-workers"

DOC_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_MATCH_MODEL = DOC_EMBEDDING_MODEL

JD_EMBEDDING_CACHE_TTL = 86400

UPLOAD_MAX_SIZE_MB = 10
UPLOAD_MAX_PAGES = 30
UPLOAD_MAX_TEXT_LENGTH = 50000
UPLOAD_ALLOWED_MIME_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
UPLOAD_ALLOWED_EXTENSIONS = {".pdf", ".docx"}

RATE_LIMIT_UPLOADS_MAX = 10
RATE_LIMIT_UPLOADS_WINDOW_SECONDS = 3600

RATE_LIMIT_MATCHES_MAX = 5
RATE_LIMIT_MATCHES_WINDOW_SECONDS = 86400

CHUNK_RETENTION_DAYS = 7
REPORT_RETENTION_DAYS = 14

RECRUITMENT_KEYWORDS = [
    r"\b(resume|curriculum\s+vitae|cv)\b",
    r"\b(experience|employment|work\s+history)\b",
    r"\b(education|degree|university|college)\b",
    r"\b(skills?|technologies|competencies|proficiencies)\b",
    r"\b(job\s+description|position|role|opening|vacancy)\b",
    r"\b(responsibilities|requirements|qualifications)\b",
    r"\b(candidate|applicant|hiring|recruitment|recruiting)\b",
    r"\b(interview|screening|onboarding)\b",
    r"\b(salary|compensation|benefits)\b",
    r"\b(match|scoring|compatibility|fit)\b",
    r"\b(skills?\s+gap|missing\s+skills?|skill\s+match)\b",
    r"\b(rewrite|optimize|improve|tailor)\b",
    r"\b(ats|applicant\s+tracking)\b",
    r"\b(portfolio|github|projects?|contributions?)\b",
]
