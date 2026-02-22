# backend/routers/settings.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import AppSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Default directives pre-populated from original hardcoded prompt context.
# Users can edit these freely in the UI.
_DEFAULT_INTERNAL_DIRECTIVE = """\
This knowledge base belongs to Cedarville University — a private Christian liberal arts university in Cedarville, Ohio.
The articles support students, faculty, and staff seeking IT help.

Key facts to reflect in rewrites:
- The IT help desk uses TeamDynamix (TDX) for ticketing and this knowledge base.
- Common systems in use: Microsoft 365 (Outlook, Teams, OneDrive, SharePoint), Banner (ERP/student information), Blackboard/Canvas (LMS), Duo (MFA), GlobalProtect VPN, CU-managed Windows and Mac devices.
- Users are a campus community — write in plain, friendly language appropriate for a university help desk. Avoid jargon; define acronyms on first use.
- Links to cedarville.edu resources should be preserved and treated as authoritative.
- If scraped source content is provided, use it to ensure accuracy and completeness — do not fabricate steps or policy details.\
"""

_DEFAULT_PUBLIC_DIRECTIVE = """\
This knowledge base belongs to Cedarville University — a private Christian liberal arts university in Cedarville, Ohio.
These articles are publicly visible and may be read by prospective students, parents, or external visitors in addition to current students, faculty, and staff.

Key facts to reflect in rewrites:
- The IT help desk uses TeamDynamix (TDX) for ticketing and this knowledge base.
- Common systems in use: Microsoft 365 (Outlook, Teams, OneDrive, SharePoint), Banner (ERP/student information), Blackboard/Canvas (LMS), Duo (MFA), GlobalProtect VPN, CU-managed Windows and Mac devices.
- Write in plain, welcoming language appropriate for a broad audience. Avoid jargon; define all acronyms on first use.
- Links to cedarville.edu resources should be preserved and treated as authoritative.
- If scraped source content is provided, use it to ensure accuracy and completeness — do not fabricate steps or policy details.\
"""


def _get_or_create(db: Session) -> AppSettings:
    row = db.query(AppSettings).first()
    if row is None:
        row = AppSettings(
            internal_directive=_DEFAULT_INTERNAL_DIRECTIVE,
            public_directive=_DEFAULT_PUBLIC_DIRECTIVE,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    row = _get_or_create(db)
    return {
        "internal_directive": row.internal_directive,
        "public_directive": row.public_directive,
    }


class SettingsPatch(BaseModel):
    internal_directive: str | None = None
    public_directive: str | None = None


@router.patch("")
def patch_settings(body: SettingsPatch, db: Session = Depends(get_db)):
    row = _get_or_create(db)
    if body.internal_directive is not None:
        row.internal_directive = body.internal_directive
    if body.public_directive is not None:
        row.public_directive = body.public_directive
    db.commit()
    db.refresh(row)
    return {
        "internal_directive": row.internal_directive,
        "public_directive": row.public_directive,
    }
