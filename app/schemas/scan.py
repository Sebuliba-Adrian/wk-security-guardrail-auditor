from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


# NOTE: FindingResponse, ScanResponse, ScanQueuedResponse, ScanHistoryItem
# are defined when api-routes module is implemented via TDD.
