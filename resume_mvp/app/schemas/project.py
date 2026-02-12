from pydantic import BaseModel, Field


class CreateProjectTextIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    target_role: str = Field(min_length=1, max_length=100)
    target_city: str | None = None
    years_experience: int | None = None
    source_text: str = Field(min_length=1)


class AnalyzeJdIn(BaseModel):
    jd_text: str = Field(min_length=1)


class RewriteIn(BaseModel):
    mode: str = Field(default="balanced")
    use_jd: bool = True


class UpdateSectionIn(BaseModel):
    optimized_text: str | None = None
    is_accepted: bool | None = None


class ExportIn(BaseModel):
    format: str = Field(default="pdf")
    template: str = Field(default="ats_default")

