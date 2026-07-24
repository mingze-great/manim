# 3004 Partner Stickman Workflow MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 3004 MVP for partner referrals, invite-code activation, `/stickman-workflow` dedicated material libraries, configurable generation controls, and isolated 3004 deployment.

**Architecture:** Extend the existing FastAPI, SQLAlchemy, React, and Remotion-adjacent workflow in place, but only inside the 3004 branch/worktree. Add partner/referral models and APIs beside the existing user/payment models. Add a dedicated `stickman_workflow_assets` service instead of reusing `stickman_v2_assets` for `/stickman-workflow`.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TypeScript, Ant Design, Nginx, systemd, Celery, Remotion render service.

## Global Constraints

- Do not modify or deploy the existing 3003 service.
- Work only in `C:\Users\Administrator\Documents\Codex\2026-07-18\300\work\3004-partner-stickman-worktree`.
- Use branch `codex/3004-partner-stickman-platform-20260724`.
- `/stickman-workflow` material-library management must not reuse `/admin/stickman-v2/scene-style-libraries`.
- Keep the default `/stickman-workflow` experience as title-only one-click generation.
- Custom script and selected target duration are mutually exclusive.
- Material-only plans must not expose real-time AI image generation to users.
- Update `PROJECT_STATE.md` before remote sync, deployment, or context handoff.
- Do not commit secrets, generated videos, uploaded files, caches, or build artifacts.

---

### Task 1: 3004 Isolated Deployment Config

**Files:**
- Create: `deploy/manim-v2-3004.conf`
- Create: `deploy/manim-v2-3004-backend.service`
- Create: `deploy/manim-v2-3004-worker.service`
- Create: `deploy/manim-v2-3004-ai-video-render.service`
- Create: `deploy/env.backend.3004.example`
- Create: `deploy/env.frontend.3004.example`
- Create: `deploy/deploy-v2-3004.sh`
- Modify: `PROJECT_STATE.md`

**Interfaces:**
- Consumes: existing 3003 deployment files as templates.
- Produces: deployable 3004 config using `/opt/manim-v2-3004-snapshot`, port `3004`, backend port `8004`, render port `18788`, queue `manim_v2_3004`.

- [ ] **Step 1: Copy 3003 deploy structure into 3004-specific files**

Use the existing 3003 deploy files as structure only, then replace every 3003 path, service name, port, queue, and nginx site name.

- [ ] **Step 2: Verify no 3004 file targets 3003 runtime**

Run:

```powershell
Select-String -Path deploy/manim-v2-3004*.*,deploy/env.*.3004.example,deploy/deploy-v2-3004.sh -Pattern 'manim-v2-3003|:3003|8003|18787|manim_v2_3003|/opt/manim-v2-3003-snapshot'
```

Expected: no output.

- [ ] **Step 3: Verify 3004 targets are present**

Run:

```powershell
Select-String -Path deploy/manim-v2-3004*.*,deploy/env.*.3004.example,deploy/deploy-v2-3004.sh -Pattern 'manim-v2-3004|:3004|8004|18788|manim_v2_3004|/opt/manim-v2-3004-snapshot'
```

Expected: output includes the 3004 service names, ports, queue, and path.

- [ ] **Step 4: Commit**

```powershell
git add deploy/manim-v2-3004.conf deploy/manim-v2-3004-backend.service deploy/manim-v2-3004-worker.service deploy/manim-v2-3004-ai-video-render.service deploy/env.backend.3004.example deploy/env.frontend.3004.example deploy/deploy-v2-3004.sh PROJECT_STATE.md
git commit -m "deploy: add isolated 3004 services"
```

### Task 2: Partner, Invite Code, and Commission Models

**Files:**
- Create: `backend/app/models/partner.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/subscription.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: SQLAlchemy models `PartnerProfile`, `ReferralCode`, `InviteCode`, `CommissionLedger`.
- Produces: user fields `role`, `referred_by_partner_id`, `referral_code`.
- Produces: order fields `partner_id`, `referral_code`, `commission_amount`, `commission_status`.

- [ ] **Step 1: Write model import smoke test**

Create `backend/tests/test_partner_models_import.py`:

```python
from app.models.partner import CommissionLedger, InviteCode, PartnerProfile, ReferralCode
from app.models.user import User
from app.models.subscription import Order


def test_partner_models_importable():
    assert PartnerProfile.__tablename__ == "partner_profiles"
    assert ReferralCode.__tablename__ == "referral_codes"
    assert InviteCode.__tablename__ == "invite_codes"
    assert CommissionLedger.__tablename__ == "commission_ledgers"
    assert hasattr(User, "role")
    assert hasattr(Order, "commission_status")
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_partner_models_import.py -q
```

Expected: FAIL because `app.models.partner` does not exist yet.

- [ ] **Step 3: Add SQLAlchemy models**

Create `backend/app/models/partner.py` with:

```python
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from app.database import Base


class PartnerProfile(Base):
    __tablename__ = "partner_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    display_name = Column(String(80), nullable=False)
    commission_rate_bps = Column(Integer, default=3000, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    settlement_info_json = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReferralCode(Base):
    __tablename__ = "referral_codes"
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partner_profiles.id"), nullable=False, index=True)
    code = Column(String(40), unique=True, nullable=False, index=True)
    channel_name = Column(String(80), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class InviteCode(Base):
    __tablename__ = "invite_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    partner_id = Column(Integer, ForeignKey("partner_profiles.id"), nullable=True, index=True)
    plan_key = Column(String(40), nullable=False)
    material_mode = Column(String(20), default="material_only", nullable=False)
    quota_limit = Column(Integer, default=0, nullable=False)
    quota_period = Column(String(20), default="daily", nullable=False)
    max_video_seconds = Column(Integer, default=60, nullable=False)
    allowed_libraries_json = Column(Text, nullable=True)
    max_uses = Column(Integer, default=1, nullable=False)
    used_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="active", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    redeemed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    redeemed_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommissionLedger(Base):
    __tablename__ = "commission_ledgers"
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partner_profiles.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    invite_code_id = Column(Integer, ForeignKey("invite_codes.id"), nullable=True, index=True)
    amount = Column(Integer, default=0, nullable=False)
    commission_rate_bps = Column(Integer, default=0, nullable=False)
    commission_amount = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    source = Column(String(30), default="order", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Add user and order columns**

Add the fields described in this task to `User` and `Order` models.

- [ ] **Step 5: Add startup migrations**

In `backend/app/main.py`, add SQLite/PostgreSQL-safe `ALTER TABLE` checks for new user/order columns and `CREATE TABLE` checks for partner tables, following the existing style.

- [ ] **Step 6: Run test and compile checks**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_partner_models_import.py -q
python -m py_compile backend/app/models/partner.py backend/app/models/user.py backend/app/models/subscription.py backend/app/main.py
```

Expected: PASS and compile exits 0.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/models/partner.py backend/app/models/user.py backend/app/models/subscription.py backend/app/models/__init__.py backend/app/main.py backend/tests/test_partner_models_import.py
git commit -m "feat: add partner referral models"
```

### Task 3: Partner, Admin, and Redeem APIs

**Files:**
- Create: `backend/app/services/partner_program.py`
- Create: `backend/app/api/partner.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/api/payment.py`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/schemas/user.py`

**Interfaces:**
- Produces: `get_current_partner_user`.
- Produces: partner APIs `GET /api/partner/profile`, `GET /api/partner/referrals`, `GET /api/partner/orders`, `GET /api/partner/commissions`, `POST /api/partner/invite-codes`.
- Produces: admin partner APIs under `/api/admin/partners`, `/api/admin/referrals`, `/api/admin/commissions`, `/api/admin/invite-codes`.
- Produces: `POST /api/payment/redeem-code`.

- [ ] **Step 1: Write service tests**

Create `backend/tests/test_partner_program_service.py`:

```python
from app.services.partner_program import estimate_commission_amount, normalize_invite_code


def test_normalize_invite_code_uppercases_and_strips():
    assert normalize_invite_code(" ab-12 ") == "AB-12"


def test_estimate_commission_amount_uses_basis_points():
    assert estimate_commission_amount(19900, 3000) == 5970
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_partner_program_service.py -q
```

Expected: FAIL because `partner_program.py` does not exist.

- [ ] **Step 3: Implement service helpers**

Create `backend/app/services/partner_program.py` with `normalize_invite_code`, `generate_invite_code`, `estimate_commission_amount`, `apply_invite_code_to_user`, `record_commission_for_order`.

- [ ] **Step 4: Implement API routes**

Add the partner, admin, and redeem endpoints listed in the interfaces. Keep response payloads minimal and non-sensitive.

- [ ] **Step 5: Register router**

Import `partner` in `backend/app/main.py` and include it with prefix `/api`.

- [ ] **Step 6: Run service tests and compile checks**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_partner_program_service.py -q
python -m py_compile backend/app/services/partner_program.py backend/app/api/partner.py backend/app/api/auth.py backend/app/api/payment.py backend/app/api/admin.py backend/app/main.py backend/app/schemas/user.py
```

Expected: PASS and compile exits 0.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/partner_program.py backend/app/api/partner.py backend/app/api/auth.py backend/app/api/payment.py backend/app/api/admin.py backend/app/main.py backend/app/schemas/user.py backend/tests/test_partner_program_service.py
git commit -m "feat: add partner and invite code APIs"
```

### Task 4: `/stickman-workflow` Dedicated Material Library Service

**Files:**
- Create: `backend/app/services/stickman_workflow_assets.py`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/api/stickman_workflow.py`
- Create: `backend/tests/test_stickman_workflow_assets.py`

**Interfaces:**
- Produces: service functions `list_material_libraries`, `save_material_libraries`, `save_material_library_package`, `public_material_libraries`, `resolve_material_library`.
- Produces: admin APIs `/api/admin/stickman-workflow/material-libraries` and `/api/admin/stickman-workflow/material-libraries/{library_key}/package`.
- Produces: public config API `/api/stickman-workflow/config`.

- [ ] **Step 1: Write asset service tests**

Create `backend/tests/test_stickman_workflow_assets.py`:

```python
from app.services.stickman_workflow_assets import normalize_material_library_items


def test_normalize_material_library_items_keeps_default_sc1():
    items = normalize_material_library_items([
        {"key": "sc1_outputs", "name": "SC1 火柴人素材库", "base_path": "/opt/manim_assets/sc1-outputs", "is_active": True}
    ])
    assert items[0]["key"] == "sc1_outputs"
    assert items[0]["base_path"] == "/opt/manim_assets/sc1-outputs"
    assert items[0]["is_active"] is True


def test_normalize_material_library_items_rejects_blank_key():
    items = normalize_material_library_items([{"key": "", "name": ""}])
    assert items == []
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_stickman_workflow_assets.py -q
```

Expected: FAIL because `stickman_workflow_assets.py` does not exist.

- [ ] **Step 3: Implement dedicated asset service**

Create `backend/app/services/stickman_workflow_assets.py`. Use a new system config key `stickman_workflow_material_libraries` and a new upload root `uploads/stickman_workflow_material_libraries`.

- [ ] **Step 4: Add admin and public APIs**

Add admin endpoints in `backend/app/api/admin.py` and user config endpoint in `backend/app/api/stickman_workflow.py`.

- [ ] **Step 5: Wire job payload**

Update `create_stickman_job` to validate selected library against `resolve_material_library` and pass normalized library metadata in payload fields `materialLibrary`, `materialLibraryPath`, and `materialLibraryManifest`.

- [ ] **Step 6: Run tests and compile checks**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_stickman_workflow_assets.py -q
python -m py_compile backend/app/services/stickman_workflow_assets.py backend/app/api/admin.py backend/app/api/stickman_workflow.py
```

Expected: PASS and compile exits 0.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/stickman_workflow_assets.py backend/app/api/admin.py backend/app/api/stickman_workflow.py backend/tests/test_stickman_workflow_assets.py
git commit -m "feat: add stickman workflow material libraries"
```

### Task 5: Stickman Workflow Controls and Quota Rules

**Files:**
- Modify: `backend/app/api/stickman_workflow.py`
- Modify: `backend/app/schemas/ai_video.py`
- Create: `backend/app/services/stickman_workflow_limits.py`
- Create: `backend/tests/test_stickman_workflow_limits.py`

**Interfaces:**
- Produces: `estimate_script_duration_seconds(script: str, speed_factor: float = 1.0) -> int`.
- Produces: payload fields `scriptMode`, `customScript`, `targetSeconds`, `backgroundMode`, `backgroundTemplate`, `uploadedBackgroundUrl`, `imageMode`.
- Enforces: `customScript` and `targetSeconds` cannot both be set.

- [ ] **Step 1: Write duration and mutual exclusion tests**

Create `backend/tests/test_stickman_workflow_limits.py`:

```python
import pytest
from app.services.stickman_workflow_limits import estimate_script_duration_seconds, validate_script_duration_request


def test_estimate_script_duration_seconds_counts_chinese_text_and_pauses():
    seconds = estimate_script_duration_seconds("你总是想太多，因为你把别人的情绪，当成了自己的责任。")
    assert 6 <= seconds <= 12


def test_validate_script_duration_request_rejects_custom_script_with_target_seconds():
    with pytest.raises(ValueError, match="自定义文案和目标时长不能同时选择"):
        validate_script_duration_request(custom_script="一段文案", target_seconds=30)
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_stickman_workflow_limits.py -q
```

Expected: FAIL because `stickman_workflow_limits.py` does not exist.

- [ ] **Step 3: Implement limits service**

Create `backend/app/services/stickman_workflow_limits.py` with duration estimation, mutual exclusion validation, max duration checks, and material mode checks.

- [ ] **Step 4: Extend job create schema and API**

Update `StickmanWorkflowJobCreate` in `backend/app/api/stickman_workflow.py` to accept advanced fields and enforce limits before creating the AI video job.

- [ ] **Step 5: Run tests and compile checks**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_stickman_workflow_limits.py -q
python -m py_compile backend/app/services/stickman_workflow_limits.py backend/app/api/stickman_workflow.py backend/app/schemas/ai_video.py
```

Expected: PASS and compile exits 0.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/stickman_workflow_limits.py backend/app/api/stickman_workflow.py backend/app/schemas/ai_video.py backend/tests/test_stickman_workflow_limits.py
git commit -m "feat: add stickman workflow generation controls"
```

### Task 6: Frontend Partner Workspace and Stickman Workflow UI

**Files:**
- Create: `frontend/src/services/partner.ts`
- Create: `frontend/src/pages/PartnerDashboard.tsx`
- Create: `frontend/src/pages/admin/AdminPartners.tsx`
- Create: `frontend/src/pages/admin/AdminStickmanWorkflowLibraries.tsx`
- Modify: `frontend/src/services/stickmanWorkflow.ts`
- Modify: `frontend/src/services/admin.ts`
- Modify: `frontend/src/stores/authStore.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout/MainLayout.tsx`
- Modify: `frontend/src/components/Layout/AdminLayout.tsx`
- Modify: `frontend/src/pages/StickmanWorkflow/index.tsx`
- Modify: `frontend/src/pages/StickmanWorkflow/StickmanWorkflow.css`

**Interfaces:**
- Produces: `/partner` route for partners.
- Produces: `/admin/partners` and `/admin/stickman-workflow-libraries`.
- Produces: `/stickman-workflow` advanced controls while keeping title-only default.

- [ ] **Step 1: Add TypeScript service contracts**

Update services so frontend can call partner APIs, admin partner APIs, `/stickman-workflow/config`, and material-library upload APIs.

- [ ] **Step 2: Add partner route guard**

Add `PartnerRoute` that allows `user.role === "partner"` or `user.is_admin`.

- [ ] **Step 3: Add partner dashboard**

Create a concise dashboard showing referral code, referrals, orders, and commissions from the partner APIs.

- [ ] **Step 4: Add admin pages**

Create admin pages for partner management and `/stickman-workflow` material libraries. The material page must label itself “火柴人工作流素材库”，not “增强讲解素材库”.

- [ ] **Step 5: Add workflow advanced controls**

Update `/stickman-workflow` page:

- title-only remains default.
- custom script mode shows text area and disables target duration.
- target duration mode disables custom script.
- material library options come from `/stickman-workflow/config`.
- image mode is hidden unless config says the user can use AI images.

- [ ] **Step 6: Run frontend checks**

Run:

```powershell
cd frontend
npm run build
```

Expected: build exits 0.

- [ ] **Step 7: Commit**

```powershell
git add frontend/src/services/partner.ts frontend/src/pages/PartnerDashboard.tsx frontend/src/pages/admin/AdminPartners.tsx frontend/src/pages/admin/AdminStickmanWorkflowLibraries.tsx frontend/src/services/stickmanWorkflow.ts frontend/src/services/admin.ts frontend/src/stores/authStore.ts frontend/src/App.tsx frontend/src/components/Layout/MainLayout.tsx frontend/src/components/Layout/AdminLayout.tsx frontend/src/pages/StickmanWorkflow/index.tsx frontend/src/pages/StickmanWorkflow/StickmanWorkflow.css
git commit -m "feat: add partner and stickman workflow UI"
```

### Task 7: 3004 Platform Verification and Deployment

**Files:**
- Modify: `PROJECT_STATE.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: 3004 remote deployment and verification record.

- [ ] **Step 1: Run local backend checks**

Run:

```powershell
$env:PYTHONPATH='backend'; pytest backend/tests/test_partner_models_import.py backend/tests/test_partner_program_service.py backend/tests/test_stickman_workflow_assets.py backend/tests/test_stickman_workflow_limits.py -q
python -m py_compile backend/app/models/partner.py backend/app/services/partner_program.py backend/app/services/stickman_workflow_assets.py backend/app/services/stickman_workflow_limits.py backend/app/api/partner.py backend/app/api/stickman_workflow.py backend/app/api/admin.py backend/app/api/payment.py backend/app/main.py
```

Expected: tests pass and compile exits 0.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
cd frontend
npm run build
```

Expected: build exits 0.

- [ ] **Step 3: Update state before remote sync**

Update `PROJECT_STATE.md` with current branch, local HEAD, planned remote directory, services, ports, and verification checklist.

- [ ] **Step 4: Deploy 3004 only**

Run the 3004 deploy script against the remote server. The deploy must target `/opt/manim-v2-3004-snapshot` and only restart 3004 services.

- [ ] **Step 5: Verify remote services**

Run:

```powershell
python scripts/remote_exec.py "systemctl is-active manim-v2-3004-backend.service manim-v2-3004-worker.service manim-v2-3004-ai-video-render.service && curl -fsS http://127.0.0.1:8004/health && curl -I -fsS http://127.0.0.1:3004/"
```

Expected: services are active, backend health succeeds, frontend responds.

- [ ] **Step 6: Verify 3003 remains untouched**

Run:

```powershell
python scripts/remote_exec.py "systemctl is-active manim-v2-3003-backend.service manim-v2-3003-worker.service manim-v2-3003-ai-video-render.service && curl -I -fsS http://127.0.0.1:3003/"
```

Expected: 3003 services are active and frontend responds.

- [ ] **Step 7: Verify `/stickman-workflow` full job on 3004**

Use browser or API to create a title-only job on `http://152.136.218.74:3004/stickman-workflow`, wait for completion, download MP4, and inspect audio/video streams with ffmpeg.

- [ ] **Step 8: Update state and commit**

Record remote HEAD, service status, job id, output path, and verification result in `PROJECT_STATE.md`.

```powershell
git add PROJECT_STATE.md
git commit -m "docs: record 3004 deployment verification"
```

## Plan Self-Review

- Spec coverage: Tasks cover 3004 isolation, partner/referral/invite/commission, `/stickman-workflow` dedicated material library, generation controls, frontend UI, deployment, and platform verification.
- Scoped deferral: reference-image-to-full-library generation is intentionally deferred to phase two because MVP must first establish dedicated material-library infrastructure.
- Placeholder scan: the plan avoids unfinished placeholders and copy-forward instructions.
- Type consistency: model and service names are consistent across tasks.
