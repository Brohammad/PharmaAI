"""
PharmaIQ – Application Settings
Loaded from environment variables / .env file.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Google Gemini ──────────────────────────────────────────────────────────
    google_api_key: str = Field("AIzaSyAJ7r-_GhXBLPcO3PrZQqvgWHbfR8iF3Yk", alias="GOOGLE_API_KEY")
    # Tier 1 operational agents (SENTINEL, PULSE, AEGIS, MERIDIAN) — fast
    gemini_model: str = Field("gemini-3.1-flash-lite-preview", alias="GEMINI_MODEL")
    # Tier 2 validation agents (CRITIQUE, COMPLIANCE) — thorough reasoning
    gemini_model_validation: str = Field("gemini-3.1-flash-lite-preview", alias="GEMINI_MODEL_VALIDATION")
    # Tier 3 meta agents (NEXUS, CHRONICLE) — deepest reasoning + synthesis
    gemini_model_synthesis: str = Field("gemini-3.1-pro-preview", alias="GEMINI_MODEL_SYNTHESIS")
    gemini_temperature: float = Field(0.1, alias="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(8192, alias="GEMINI_MAX_TOKENS")
    environment: str = Field("development", alias="ENVIRONMENT")

    # ── MedChain identity ─────────────────────────────────────────────────────
    total_stores: int = Field(320, alias="TOTAL_STORES")
    total_fridge_units: int = Field(960, alias="TOTAL_FRIDGE_UNITS")
    annual_revenue_crore: float = Field(840.0, alias="ANNUAL_REVENUE_CRORE")

    # ── MCP Server base URLs ───────────────────────────────────────────────────
    mcp_cold_chain_url: str = Field("http://localhost:8101", alias="MCP_COLD_CHAIN_URL")
    mcp_erp_url: str = Field("http://localhost:8102", alias="MCP_ERP_URL")
    mcp_hrms_url: str = Field("http://localhost:8103", alias="MCP_HRMS_URL")
    mcp_distributor_url: str = Field("http://localhost:8104", alias="MCP_DISTRIBUTOR_URL")
    mcp_external_intel_url: str = Field("http://localhost:8105", alias="MCP_EXTERNAL_INTEL_URL")
    mcp_regulatory_kb_url: str = Field("http://localhost:8106", alias="MCP_REGULATORY_KB_URL")
    mcp_communication_url: str = Field("http://localhost:8107", alias="MCP_COMMUNICATION_URL")

    # ── Authority thresholds ───────────────────────────────────────────────────
    auto_order_max_multiplier: float = Field(2.5, alias="AUTO_ORDER_MAX_MULTIPLIER")
    human_informed_order_max_multiplier: float = Field(3.0, alias="HUMAN_INFORMED_ORDER_MAX_MULTIPLIER")
    high_cost_action_threshold_lakh: float = Field(2.0, alias="HIGH_COST_ACTION_THRESHOLD_LAKH")

    # ── Cold chain alert thresholds ────────────────────────────────────────────
    cold_chain_normal_min_temp: float = Field(2.0, alias="COLD_CHAIN_NORMAL_MIN_TEMP")
    cold_chain_normal_max_temp: float = Field(8.0, alias="COLD_CHAIN_NORMAL_MAX_TEMP")
    cold_chain_moderate_max_temp: float = Field(15.0, alias="COLD_CHAIN_MODERATE_MAX_TEMP")
    cold_chain_severe_temp: float = Field(15.0, alias="COLD_CHAIN_SEVERE_TEMP")
    cold_chain_freeze_temp: float = Field(0.0, alias="COLD_CHAIN_FREEZE_TEMP")
    cold_chain_sensor_offline_minutes: int = Field(5, alias="COLD_CHAIN_SENSOR_OFFLINE_MINUTES")

    # ── CRITIQUE thresholds ────────────────────────────────────────────────────
    critique_min_challenge_rate: float = Field(0.15, alias="CRITIQUE_MIN_CHALLENGE_RATE")
    critique_max_challenge_rate: float = Field(0.30, alias="CRITIQUE_MAX_CHALLENGE_RATE")

    # ── Scheduled cycle times (24h format) ────────────────────────────────────
    morning_forecast_hour: int = Field(5, alias="MORNING_FORECAST_HOUR")
    midday_reforecast_hour: int = Field(13, alias="MIDDAY_REFORECAST_HOUR")
    compliance_sweep_interval_hours: int = Field(2, alias="COMPLIANCE_SWEEP_INTERVAL_HOURS")
    expiry_review_hour: int = Field(22, alias="EXPIRY_REVIEW_HOUR")
    weekly_brief_weekday: int = Field(0, alias="WEEKLY_BRIEF_WEEKDAY")  # 0 = Monday
    weekly_brief_hour: int = Field(7, alias="WEEKLY_BRIEF_HOUR")

    # ── Operational KPI targets ────────────────────────────────────────────────
    target_mttd_minutes: int = Field(5, alias="TARGET_MTTD_MINUTES")
    target_cold_chain_fp_rate: float = Field(0.05, alias="TARGET_COLD_CHAIN_FP_RATE")
    target_demand_mape: float = Field(0.18, alias="TARGET_DEMAND_MAPE")
    target_epidemic_lead_days: int = Field(5, alias="TARGET_EPIDEMIC_LEAD_DAYS")
    target_stockout_rate: float = Field(0.02, alias="TARGET_STOCKOUT_RATE")
    target_expiry_writeoff_rate: float = Field(0.008, alias="TARGET_EXPIRY_WRITEOFF_RATE")
    target_schedule_h_compliance: float = Field(1.0, alias="TARGET_SCHEDULE_H_COMPLIANCE")
    target_staff_utilisation: float = Field(0.80, alias="TARGET_STAFF_UTILISATION")

    # ── Logging ────────────────────────────────────────────────────────────────
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    audit_log_path: str = Field("logs/audit.jsonl", alias="AUDIT_LOG_PATH")

    # ── FastAPI ────────────────────────────────────────────────────────────────
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")
    api_reload: bool = Field(False, alias="API_RELOAD")


settings = Settings()
