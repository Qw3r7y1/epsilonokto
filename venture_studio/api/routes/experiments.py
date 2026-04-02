"""API routes for experiments."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from venture_studio.db.models import Experiment, ExperimentStatus
from venture_studio.db.session import get_db
from venture_studio.schemas.experiments import (
    ExperimentCreate,
    ExperimentOut,
    ExperimentUpdate,
)
from venture_studio.services.orchestrator import Orchestrator

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/", response_model=list[ExperimentOut])
async def list_experiments(
    status: ExperimentStatus | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Experiment).offset(offset).limit(limit).order_by(Experiment.created_at.desc())
    if status:
        q = q.where(Experiment.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{experiment_id}", response_model=ExperimentOut)
async def get_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")
    return exp


@router.post("/", response_model=ExperimentOut, status_code=201)
async def create_experiment(body: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    exp = Experiment(**body.model_dump(by_alias=False, exclude_none=True))
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    return exp


@router.patch("/{experiment_id}", response_model=ExperimentOut)
async def update_experiment(
    experiment_id: uuid.UUID,
    body: ExperimentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Experiment).where(Experiment.id == experiment_id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, "Experiment not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(exp, field, value)
    await db.commit()
    await db.refresh(exp)
    return exp


@router.post("/{experiment_id}/advance")
async def advance_experiment(experiment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    orch = Orchestrator(db)
    result = await orch.advance_experiment(experiment_id)
    return result
