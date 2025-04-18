import time
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T", bound=BaseModel)

# === Base ===


class BaseRequest(BaseModel):
    """Base request"""

    type: str
    request_id: Optional[str] = None
    output_topic: Optional[str] = None
    output_partition: Optional[int] = None


class BaseResponse(BaseModel):
    """Base response"""

    type: str
    request_id: str


# === Chat ===


class ImageUrlContent(BaseModel):
    """Image URL content for chat requests"""

    url: str


class ContentItem(BaseModel):
    """Content item for chat requests"""

    type: str
    text: Optional[str] = None
    image_url: Optional[ImageUrlContent] = None


class MessageItem(BaseModel):
    """Message item for chat requests"""

    role: str
    content: Union[str, List[ContentItem]]  # Updated to allow a list of ContentItem


class Prompt(BaseModel):
    """Prompt for chat requests"""

    messages: List[MessageItem]


class SamplingParams(BaseModel):
    """Sampling parameters for chat requests"""

    n: int = 1
    best_of: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    repetition_penalty: float = 1.0
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = -1
    min_p: float = 0.0
    seed: Optional[int] = None
    stop: Optional[List[str]] = None
    stop_token_ids: Optional[List[int]] = None
    min_tokens: int = 0
    logprobs: Optional[int] = None
    prompt_logprobs: Optional[int] = None
    detokenize: bool = True
    skip_special_tokens: bool = True
    spaces_between_special_tokens: bool = True
    truncate_prompt_tokens: Optional[int] = None


class Usage(BaseModel):
    """Usage for chat requests"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatRequest(BaseRequest):
    """Chat request"""

    type: str = "ChatRequest"
    model: Optional[str] = None
    kind: Optional[str] = None
    provider: Optional[str] = None
    namespace: Optional[str] = None
    adapter: Optional[str] = None
    prompt: Optional[Prompt] = None
    batch: Optional[List[Prompt]] = None
    max_tokens: int = Field(default=512)
    sampling_params: SamplingParams = Field(default_factory=SamplingParams)
    stream: bool = False
    user_id: Optional[str] = None
    organizations: Optional[Dict[str, Dict[str, str]]] = None
    handle: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def replace_none_with_default(cls, values: dict) -> dict:
        if "max_tokens" in values and values["max_tokens"] is None:
            values["max_tokens"] = 512
        if "sampling_params" in values and values["sampling_params"] is None:
            values["sampling_params"] = SamplingParams()
        return values


class Choice(BaseModel):
    """Individual choice in the token response"""

    index: int
    text: str
    tokens: Optional[List[str]] = None
    token_ids: Optional[List[int]] = None
    logprobs: Optional[List[Dict[Union[int, str], Any]]] = None
    finish_reason: Optional[str] = None


class ChatResponse(BaseResponse, Generic[T]):
    """Chat response"""

    type: str = "ChatResponse"
    choices: List[Choice]
    trip_time: Optional[float] = None
    usage: Optional[Usage] = None
    parsed: Optional[T] = None


class TokenResponse(BaseResponse):
    """Token response"""

    type: str = "TokenResponse"
    choices: List[Choice]
    usage: Optional[Usage] = None


class V1ChatEvent(BaseModel):
    """
    Chat event containing both the request and response, along with additional metadata.
    """

    request: ChatRequest
    response: ChatResponse
    token_count: Optional[int] = None
    trip_time: Optional[float] = None
    approved: Optional[bool] = None
    metadata: Optional[Dict[str, str]] = None
    owner_id: Optional[str] = None
    organization_id: Optional[str] = None
    handle: Optional[str] = None
    created: Optional[int] = None


# === Completion ===


class CompletionRequest(BaseModel):
    """Request for completion requests"""

    text: str
    images: Optional[List[str]] = None


class CompletionResponse(BaseResponse):
    """Completion response"""

    type: str = "CompletionResponse"
    choices: List[Choice]
    trip_time: Optional[float] = None
    usage: Optional[Usage] = None


# === OCR ===


class OCRRequest(BaseRequest):
    """Simple OCR request following EasyOCR patterns"""

    type: str = "OCRRequest"
    model: Optional[str] = None
    provider: Optional[str] = None
    image: str
    languages: List[str]  # e.g. ['en'], ['ch_sim', 'en']
    gpu: bool = True
    detail: bool = True  # True returns bounding boxes, False returns just text
    paragraph: bool = False  # Merge text into paragraphs
    min_confidence: Optional[float] = 0.0


class BoundingBox(BaseModel):
    """Coordinates for text location: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"""

    points: List[List[int]]  # List of 4 points (8 coordinates total)
    text: str
    confidence: float


class OCRResponse(BaseResponse):
    """Response containing detected text and locations"""

    type: str = "OCRResponse"
    results: Union[List[BoundingBox], List[str]]  # List[str] if detail=False
    processing_time: Optional[float] = None
    usage: Optional[Usage] = None


# === Embeddings ===


class EmbeddingRequest(BaseRequest):
    """Embedding request"""

    type: str = "EmbeddingRequest"
    model: Optional[str] = None
    provider: Optional[str] = None
    text: Optional[str] = None
    image: Optional[str] = None


class Embedding(BaseModel):
    """Embedding"""

    object: str
    index: int
    embedding: List[float]


class EmbeddingResponse(BaseResponse):
    """Embedding response"""

    type: str = "EmbeddingResponse"
    object: str
    data: List[Embedding]
    model: str
    usage: Optional[Usage] = None


# === Deployments ===


class V1ReplicasInfo(BaseModel):
    """
    Replica status information for a given deployment.
    """

    desired: int = 0
    ready: int = 0
    updated: int = 0
    available: int = 0
    unavailable: int = 0


class V1VLLMParams(BaseModel):
    """
    Configuration parameters for vLLM-based deployments.
    """

    model: str
    model_type: Optional[str] = None
    trust_remote_code: bool = True
    tensor_parallel_size: int = 1
    dtype: str = "auto"
    max_images_per_prompt: int = 1
    device: str = "cuda"
    max_model_len: int = 8192
    max_num_seqs: int = 5
    gpu_memory_utilization: float = 0.8
    enforce_eager: bool = True
    enable_adapter: bool = False


class V1SentenceTFParams(BaseModel):
    """
    Configuration parameters for SentenceTransformers-based deployments.
    """

    model: str = "clip-ViT-B-32"
    device: str = "cuda"


class V1DoctrParams(BaseModel):
    """
    Configuration parameters for doctr-based OCR deployments.
    """

    det_arch: str = "fast_base"
    reco_arch: str = "crnn_vgg16_bn"
    pretrained: bool = True


class V1EasyOCRParams(BaseModel):
    """
    Configuration parameters for EasyOCR-based deployments.
    """

    device: str = "cuda"
    gpu: bool = True
    lang_list: List[str] = Field(default_factory=lambda: ["en"])
    quantize: bool = False


class V1LiteLLMParams(BaseModel):
    """
    Configuration parameters for LiteLLM-based deployments.
    """

    api_keys: Dict[str, str] = Field(default_factory=dict)


class V1ModelDeployment(BaseModel):
    """
    A model deployment, containing configuration and current status for a running model.
    """

    id: str = ""
    namespace: str = ""
    provider: str = ""
    kind: str = ""
    replicas: Optional[V1ReplicasInfo] = None
    status: str = ""
    image: str = ""
    vram_request: str = ""
    gpu_type: Optional[str] = None
    cpu_request: Optional[str] = None
    vllm_params: Optional[V1VLLMParams] = None
    sentence_tf_params: Optional[V1SentenceTFParams] = None
    doctr_params: Optional[V1DoctrParams] = None
    easyocr_params: Optional[V1EasyOCRParams] = None
    litellm_params: Optional[V1LiteLLMParams] = None


class V1ModelDeploymentRequest(BaseModel):
    """
    Request structure for creating or updating a model deployment.
    """

    namespace: Optional[str] = None
    provider: str
    vram_request: str
    memory_request: Optional[str] = None
    cpu_request: Optional[str] = None
    vllm_params: Optional[V1VLLMParams] = None
    sentence_tf_params: Optional[V1SentenceTFParams] = None
    doctr_params: Optional[V1DoctrParams] = None
    easyocr_params: Optional[V1EasyOCRParams] = None
    litellm_params: Optional[V1LiteLLMParams] = None
    max_pixels: Optional[int] = None


# === Training & Buffers ===


class V1LlamaFactoryParams(BaseModel):
    """
    LlamaFactoryParams
    """

    model: str = ""


class V1MSSwiftParams(BaseModel):
    """
    MSSwiftParams
    """

    model: str = "Qwen/Qwen2-VL-7B-Instruct"
    model_type: str = "qwen2-vl-7b-instruct"
    train_type: str = "lora"
    deepspeed: str = "zero3"
    torch_dtype: str = "bfloat16"
    max_length: int = 8192
    dataset: str = ""
    val_split_ratio: float = 0.90
    num_train_epochs: int = 3
    eval_strategy: str = "epoch"
    save_strategy: str = "epoch"
    save_total_limit: int = 3
    lora_rank: Optional[int] = None
    lora_alpha: Optional[int] = None
    size_factor: int = 28
    max_pixels: int = 1025000
    resume_from_checkpoint: Optional[str] = None
    freeze_vit: Optional[bool] = None


class V1TrainingRequest(BaseModel):
    """
    Request to create a new training job
    """

    name: Optional[str] = None
    namespace: Optional[str] = None
    provider: str
    vram_request: str
    cpu_request: Optional[str] = None
    trust_remote_code: Optional[bool] = None
    adapter: Optional[str] = None
    buffer: Optional[str] = None
    queue: Optional[str] = None
    ms_swift_params: Optional[V1MSSwiftParams] = None
    llama_factory_params: Optional[V1LlamaFactoryParams] = None
    resume: Optional[bool] = None
    labels: Optional[Dict[str, str]] = None


class V1Checkpoint(BaseModel):
    """
    Checkpoint with step count and optional artifacts
    """

    step: int = 0
    trainer_state: Optional[str] = None
    args: Optional[str] = None
    adapter_config: Optional[str] = None


class V1TrainingJob(BaseModel):
    """
    Information about an existing training job
    """

    id: str
    name: str = ""
    namespace: str = ""
    provider: str = ""
    vram_request: str = ""
    cpu_request: Optional[str] = None
    trust_remote_code: Optional[bool] = None
    adapter: Optional[str] = None
    buffer: Optional[str] = None
    ms_swift_params: Optional[V1MSSwiftParams] = None
    llama_factory_params: Optional[V1LlamaFactoryParams] = None
    resume: Optional[bool] = None
    status: str = ""
    checkpoints: Optional[List[V1Checkpoint]] = None
    queue: Optional[str] = None
    labels: Optional[Dict[str, str]] = None
    created: int = Field(default_factory=lambda: int(time.time()))
    updated: int = Field(default_factory=lambda: int(time.time()))


class V1TrainingJobsResponse(BaseModel):
    """
    A list of training jobs
    """

    jobs: List[V1TrainingJob] = Field(default_factory=list)


class V1MSSwiftBufferParams(BaseModel):
    """
    MSSwiftParams variant for buffer-based training
    """

    model: str = "Qwen/Qwen2-VL-7B-Instruct"
    model_type: str = "qwen2-vl-7b-instruct"
    train_type: str = "lora"
    deepspeed: str = "zero3"
    torch_dtype: str = "bfloat16"
    max_length: int = 8192
    val_split_ratio: float = 0.90
    num_train_epochs: int = 3
    eval_strategy: str = "epoch"
    save_strategy: str = "epoch"
    save_total_limit: int = 3
    lora_rank: Optional[int] = None
    lora_alpha: Optional[int] = None
    size_factor: int = 28
    max_pixels: int = 1025000
    resume_from_checkpoint: Optional[str] = None
    freeze_vit: Optional[bool] = None


class V1ReplayBufferRequest(BaseModel):
    """
    Request to create a replay buffer for incremental training
    """

    name: str
    namespace: Optional[str] = None
    provider: str
    vram_request: str
    cpu_request: Optional[str] = None
    trust_remote_code: Optional[bool] = None
    adapter: Optional[str] = None
    train_every: int = 50
    sample_n: int = 100
    sample_strategy: str = "Random"
    queue: Optional[str] = None
    ms_swift_params: Optional[V1MSSwiftBufferParams] = None
    llama_factory_params: Optional[V1LlamaFactoryParams] = None
    labels: Optional[Dict[str, str]] = None


class V1ReplayBuffer(BaseModel):
    """
    A replay buffer used for incremental training
    """

    id: str = ""
    name: str = ""
    namespace: str = ""
    provider: str = ""
    vram_request: str = ""
    cpu_request: Optional[str] = None
    trust_remote_code: Optional[bool] = None
    adapter: Optional[str] = None
    train_every: Optional[int] = None
    sample_n: int = 100
    sample_strategy: str = "Random"
    ms_swift_params: Optional[V1MSSwiftBufferParams] = None
    llama_factory_params: Optional[V1LlamaFactoryParams] = None
    labels: Optional[Dict[str, str]] = None
    queue: Optional[str] = None
    num_records: Optional[int] = None
    train_idx: Optional[int] = None


class V1ReplayBuffersResponse(BaseModel):
    """
    A list of replay buffers
    """

    buffers: List[V1ReplayBuffer] = Field(default_factory=list)


class V1ReplayBufferData(BaseModel):
    """
    The data stored in the replay buffer
    """

    examples: List[dict] = Field(default_factory=list)


class V1Adapters(BaseModel):
    """
    A list of known adapters
    """

    adapters: List[str] = Field(default_factory=list)


class V1Models(BaseModel):
    """
    A list of known models
    """

    models: List[str] = Field(default_factory=list)


class V1Datasets(BaseModel):
    """
    A list of known datasets
    """

    datasets: List[str] = Field(default_factory=list)


class V1ModelFile(BaseModel):
    """
    Information about the latest checkpoint file
    """

    latest_checkpoint: Optional[str] = None


# === Errors ===


class ErrorResponse(BaseResponse):
    """Error response"""

    type: str = "ErrorResponse"
    error: str
    traceback: Optional[str] = None


# === Model ===


class ModelReadyResponse(BaseResponse):
    """Response indicating if a model is ready"""

    type: str = "ModelReadyResponse"
    request_id: str
    ready: bool
    error: Optional[str] = None
