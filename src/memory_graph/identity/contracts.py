"""Evidence has no authority; all contracts are immutable value objects."""
from dataclasses import dataclass, asdict
import hashlib, json, math

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()

def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0.

def cosine(a,b):
    if not a or not b or len(a)!=len(b):return None
    return sum(x*y for x,y in zip(a,b))/math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))

@dataclass(frozen=True)
class Policy:
    sample_fps: float = 5.
    gap_seconds: float = .4
    minimum_binding_observations: int = 3
    minimum_binding_span: float = .4
    minimum_confidence: float = .5
    binding_quality_margin: float = .1
    admission_similarity: float = .6
    physical_competitor_margin: float = .1
    support_iou: float = .3
    continuity_iou: float = .05
    coexistence_iou: float = .1
    minimum_prototypes: int = 2
    persistence_observations: int = 3
    persistence_span: float = .4
    automatic_confirmation_enabled: bool = False
    calibration_id: str = 'DEVELOPMENT_INSUFFICIENT_FOR_STRONG_CONFIRMATION'

@dataclass(frozen=True)
class Observation:
    observation_id: str
    candidate_id: str
    frame: int
    time: float
    bbox: tuple
    label: str
    confidence: float
    provenance: str
    vector: tuple = ()
    sam_overlap: float = 0.
    drift: bool = False
    scene_break: bool = False
    mask_reference: str | None = None
    source: str = 'yolo_track'

    def __post_init__(self):
        object.__setattr__(self,'bbox',tuple(self.bbox))
        object.__setattr__(self,'vector',tuple(self.vector))
        if len(self.bbox)!=4 or not all(math.isfinite(x) for x in (*self.bbox,self.time,self.confidence,self.sam_overlap,*self.vector)):
            raise ValueError('Nonfinite/invalid observation')
        if self.bbox[2]<=self.bbox[0] or self.bbox[3]<=self.bbox[1] or self.time<0 or self.frame<0:
            raise ValueError('Invalid geometry/time')
        if not 0<=self.confidence<=1 or not 0<=self.sam_overlap<=1:raise ValueError('Invalid probability')
        if self.vector and sum(x*x for x in self.vector)<=0:raise ValueError('Zero embedding')
        if not self.observation_id or not self.candidate_id or not self.provenance:raise ValueError('Missing provenance')

    def data(self):return asdict(self)
    @property
    def phone(self):return self.label in {'cell phone','phone','smartphone'}
