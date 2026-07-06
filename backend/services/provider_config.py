PROVIDER_CONFIGS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini", "o3-mini"],
    },
    "nvidia": {
        "name": "NVIDIA AI",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "mistralai/mistral-large-3-675b-instruct-2512",
        "models": [
            "mistralai/mistral-large-3-675b-instruct-2512",
            "meta/llama-3.1-405b-instruct",
            "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        ],
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "deepseek-r1-distill-llama-70b",
        ],
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "default_model": "mistralai/Mistral-7B-Instruct-v0.3",
        "models": [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        ],
    },
    "custom": {
        "name": "Custom (OpenAI-compatible)",
        "base_url": "",
        "default_model": "",
        "models": [],
    },
}
