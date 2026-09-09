# API Chaos Tester - Intelligent API Fuzz Testing
# Author: Maharshi Soni | License: MIT
"""
Mock FastAPI server for testing the chaos tester against a real HTTP API.
Implements the petstore spec with intentional validation and a few
deliberately weak spots to demonstrate chaos testing value.

Run with:
    uvicorn samples.mock_server:app --port 8000
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Sample Pet Store", version="1.0.0")

# In-memory store
_pets: dict[int, dict] = {
    1: {"id": 1, "name": "Buddy", "species": "dog", "age": 3, "weight": 15.0, "vaccinated": True, "tags": ["friendly"]},
    2: {"id": 2, "name": "Whiskers", "species": "cat", "age": 5, "weight": 4.5, "vaccinated": False, "tags": ["indoor"]},
}
_next_id = 3


class PetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    species: str
    age: Optional[int] = Field(default=None, ge=0, le=50)
    weight: Optional[float] = Field(default=None, ge=0.1, le=500.0)
    vaccinated: Optional[bool] = None
    tags: Optional[list[str]] = None


class PetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    age: Optional[int] = Field(default=None, ge=0, le=50)
    weight: Optional[float] = Field(default=None, ge=0.1)


class VaccinationRecord(BaseModel):
    vaccine_name: str = Field(min_length=1, max_length=200)
    date: str
    notes: Optional[str] = Field(default=None, max_length=1000)


@app.get("/pets")
def list_pets(
    limit: int = Query(default=20, ge=1, le=100),
    species: Optional[str] = None,
    name: Optional[str] = None,
) -> list[dict]:
    """List all pets with optional filtering."""
    pets = list(_pets.values())
    if species:
        pets = [p for p in pets if p.get("species") == species]
    if name:
        pets = [p for p in pets if name.lower() in p.get("name", "").lower()]
    return pets[:limit]


@app.post("/pets", status_code=201)
def create_pet(pet: PetCreate) -> dict:
    """Create a new pet."""
    global _next_id
    valid_species = {"dog", "cat", "bird", "fish"}
    if pet.species not in valid_species:
        raise HTTPException(status_code=422, detail=f"Invalid species. Must be one of: {valid_species}")

    pet_dict = pet.model_dump()
    pet_dict["id"] = _next_id
    _pets[_next_id] = pet_dict
    _next_id += 1
    return pet_dict


@app.get("/pets/{pet_id}")
def get_pet(pet_id: int) -> dict:
    """Get a pet by ID."""
    if pet_id not in _pets:
        raise HTTPException(status_code=404, detail="Pet not found")
    return _pets[pet_id]


@app.put("/pets/{pet_id}")
def update_pet(pet_id: int, update: PetUpdate) -> dict:
    """Update a pet."""
    if pet_id not in _pets:
        raise HTTPException(status_code=404, detail="Pet not found")
    pet = _pets[pet_id]
    update_data = update.model_dump(exclude_unset=True)
    pet.update(update_data)
    return pet


@app.delete("/pets/{pet_id}", status_code=204)
def delete_pet(pet_id: int) -> None:
    """Delete a pet."""
    if pet_id not in _pets:
        raise HTTPException(status_code=404, detail="Pet not found")
    del _pets[pet_id]


@app.post("/pets/{pet_id}/vaccinations", status_code=201)
def add_vaccination(pet_id: int, record: VaccinationRecord) -> dict:
    """Record a vaccination for a pet."""
    if pet_id not in _pets:
        raise HTTPException(status_code=404, detail="Pet not found")
    return {
        "pet_id": pet_id,
        "vaccine_name": record.vaccine_name,
        "date": record.date,
        "notes": record.notes,
        "status": "recorded",
    }


@app.get("/search")
def search_pets(
    q: str = Query(min_length=1, max_length=200),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Search for pets."""
    results = [
        p for p in _pets.values()
        if q.lower() in p.get("name", "").lower()
        or q.lower() in p.get("species", "").lower()
    ]
    start = (page - 1) * per_page
    return {
        "query": q,
        "total": len(results),
        "page": page,
        "results": results[start : start + per_page],
    }
