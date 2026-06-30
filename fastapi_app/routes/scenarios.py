from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session

from fastapi_app.core.dependencies import get_current_user
from fastapi_app.db.session import get_db
from fastapi_app.models.auth_model import User
from fastapi_app.schemas.scenario_schema import (
    ScenarioCreate,
    ScenarioResponse,
    ScenarioUpdate,
)
from fastapi_app.services.scenario.scenario_service import ScenarioService

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


@router.get("", response_model=List[ScenarioResponse])
def list_scenarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ScenarioService.get_all_scenarios(db)


@router.post("", response_model=ScenarioResponse)
def create_scenario(
    payload: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ScenarioService.create_scenario(db, payload)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = ScenarioService.get_scenario_by_id(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = ScenarioService.update_scenario(db, scenario_id, payload)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not ScenarioService.delete_scenario(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"deleted": True}


@router.post("/{scenario_id}/run", response_model=ScenarioResponse)
def run_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scenario = ScenarioService.run_scenario(db, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario
