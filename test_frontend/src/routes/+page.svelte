<script>
    import { onMount } from 'svelte';

    // State variables
    let inputText = '';
    let isProcessing = false;
    let currentStep = '';
    let error = null;
    let results = {
        paraphrased: '',
        rewritten: '',
        final: ''
    };
    let statistics = {};
    let processingSteps = [];

    // Multi-model results
    let multiResults = null;
    let allResults = null;
    let showMultiResults = false;

    // Configuration - simplified
    let availableModels = [];
    let currentModel = '';
    let selectedModel = '';
    let useEnhanced = false;
    let backendStatus = null;

    // Processing modes
    let processingMode = 'single';

    // AI Detection state
    let detectionResults = null;
    let isDetecting = false;
    let detectionMode = 'ensemble'; // ensemble, simple, single, segments
    let selectedDetectionModel = 'chatgpt-detector';
    let detectionThreshold = 0.7;
    let segmentLength = 200;
    let availableDetectionModels = [];
    let showDetectionResults = false;

    // Combined processing state
    let combinedResults = null;
    let showCombinedResults = false;

    // API base URL
    const API_BASE = 'http://localhost:8080';

    // Error logging function
    function logError(context, error, additionalData = {}) {
        const errorLog = {
            timestamp: new Date().toISOString(),
            context: context,
            error: error.message || error.toString(),
            stack: error.stack,
            url: window.location.href,
            userAgent: navigator.userAgent,
            additionalData: additionalData
        };
        
        console.error(`[${context}] Error:`, errorLog);
        return errorLog;
    }

    // Copy to clipboard functionality
    async function copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            showToast('Copied to clipboard!');
        } catch (err) {
            logError('copyToClipboard', err, { textLength: text.length });
            console.error('Failed to copy: ', err);
            showToast('Failed to copy to clipboard', 'error');
        }
    }

    // Toast notification system
    let toastMessage = '';
    let toastType = 'success';
    let showToastFlag = false;

    function showToast(message, type = 'success') {
        toastMessage = message;
        toastType = type;
        showToastFlag = true;
        setTimeout(() => {
            showToastFlag = false;
        }, 3000);
    }

    // Load backend status and models
    async function loadBackendInfo() {
        try {
            const response = await fetch(`${API_BASE}/health`);
            if (response.ok) {
                backendStatus = await response.json();
            } else {
                throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
            }

            const modelsResponse = await fetch(`${API_BASE}/models`);
            if (modelsResponse.ok) {
                const modelsData = await modelsResponse.json();
                availableModels = modelsData.available_models || [];
                currentModel = modelsData.current_model || '';
                selectedModel = currentModel;
            } else {
                throw new Error(`Models fetch failed: ${modelsResponse.status} ${modelsResponse.statusText}`);
            }
        } catch (err) {
            logError('loadBackendInfo', err, { API_BASE });
            console.error('Failed to load backend info:', err);
            error = 'Failed to connect to backend service';
        }
    }

    // Load specific model
    async function loadModel(modelName) {
        if (!modelName || modelName === currentModel) return;

        try {
            const response = await fetch(`${API_BASE}/load_model`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });

            if (response.ok) {
                const data = await response.json();
                currentModel = data.current_model;
                showToast(`Model ${modelName} loaded successfully`);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || `Failed to load model: ${response.status}`);
            }
        } catch (err) {
            logError('loadModel', err, { modelName, currentModel });
            console.error('Failed to load model:', err);
            showToast(`Failed to load model: ${err.message}`, 'error');
        }
    }

    // Validate input text
    function validateInput() {
        if (!inputText.trim()) {
            showToast('Please enter some text to humanize', 'error');
            return false;
        }

        if (inputText.length < 10) {
            showToast('Text must be at least 10 characters long', 'error');
            return false;
        }

        if (inputText.length > 5000) {
            showToast('Text must be less than 5000 characters', 'error');
            return false;
        }

        return true;
    }

    // Reset results
    function resetResults() {
        results = { paraphrased: '', rewritten: '', final: '' };
        statistics = {};
        processingSteps = [];
        multiResults = null;
        allResults = null;
        showMultiResults = false;
        error = null;
    }

    // Single model humanization (paraphrase + rewrite)
    async function humanizeWithSingleModel() {
        if (!validateInput()) return;

        isProcessing = true;
        currentStep = '';
        resetResults();
        processingMode = 'single';

        try {
            // Load selected model if different from current
            if (selectedModel && selectedModel !== currentModel) {
                await loadModel(selectedModel);
            }

            // Step 1: Paraphrasing
            currentStep = 'paraphrasing';
            const paraphraseResponse = await fetch(`${API_BASE}/paraphrase_only`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: inputText,
                    model: selectedModel
                })
            });

            if (paraphraseResponse.ok) {
                const paraphraseData = await paraphraseResponse.json();
                results.paraphrased = paraphraseData.paraphrased_text;
                statistics = { ...statistics, ...paraphraseData.statistics };
                
                // Show paraphrased result briefly
                await new Promise(resolve => setTimeout(resolve, 1000));
            } else {
                const errorData = await paraphraseResponse.json();
                throw new Error(errorData.error || 'Paraphrasing failed');
            }

            // Step 2: Rewriting
            currentStep = 'rewriting';
            const rewriteResponse = await fetch(`${API_BASE}/rewrite_only`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: results.paraphrased,
                    enhanced: useEnhanced
                })
            });

            if (rewriteResponse.ok) {
                const rewriteData = await rewriteResponse.json();
                results.rewritten = rewriteData.rewritten_text;
                results.final = rewriteData.rewritten_text;
                statistics = { 
                    ...statistics, 
                    ...rewriteData.statistics,
                    final_length: rewriteData.statistics.rewritten_length,
                    enhanced_rewriting_used: useEnhanced
                };
                
                currentStep = 'complete';
                showToast('Text humanized successfully!');
            } else {
                const errorData = await rewriteResponse.json();
                throw new Error(errorData.error || 'Rewriting failed');
            }

        } catch (err) {
            logError('humanizeWithSingleModel', err, { 
                inputLength: inputText.length,
                useEnhanced,
                selectedModel
            });
            error = err.message;
            showToast(error, 'error');
        } finally {
            isProcessing = false;
            currentStep = 'complete';
        }
    }

    // Multi-model paraphrasing (2 best models in pipeline)
    async function paraphraseWithMultiModels() {
        if (!validateInput()) return;

        isProcessing = true;
        currentStep = 'paraphrasing';
        resetResults();
        processingMode = 'multi';

        try {
            const response = await fetch(`${API_BASE}/paraphrase_multi`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: inputText })
            });

            if (response.ok) {
                multiResults = await response.json();
                showMultiResults = true;
                showToast(`Pipeline completed! ${multiResults.statistics.successful_steps}/${multiResults.statistics.pipeline_steps} steps successful.`);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || `Multi-model paraphrasing failed: ${response.status}`);
            }
        } catch (err) {
            logError('paraphraseWithMultiModels', err, { 
                inputLength: inputText.length,
                processingMode 
            });
            error = err.message;
            showToast(error, 'error');
        } finally {
            isProcessing = false;
            currentStep = 'complete';
        }
    }

    // All models paraphrasing (all models in pipeline)
    async function paraphraseWithAllModels() {
        if (!validateInput()) return;

        isProcessing = true;
        currentStep = 'paraphrasing';
        resetResults();
        processingMode = 'all';

        try {
            const response = await fetch(`${API_BASE}/paraphrase_all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: inputText })
            });

            if (response.ok) {
                allResults = await response.json();
                showMultiResults = true;
                showToast(`Pipeline completed! ${allResults.statistics.successful_steps}/${allResults.statistics.pipeline_steps} steps successful in ${allResults.statistics.total_processing_time}s.`);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || `All-models paraphrasing failed: ${response.status}`);
            }
        } catch (err) {
            logError('paraphraseWithAllModels', err, { 
                inputLength: inputText.length,
                processingMode,
                availableModelsCount: availableModels.length
            });
            error = err.message;
            showToast(error, 'error');
        } finally {
            isProcessing = false;
            currentStep = 'complete';
        }
    }

    // Continue a paraphrased result to rewriting
    async function continueToRewrite(paraphrasedText, modelUsed = null) {
        isProcessing = true;
        currentStep = 'rewriting';
        showMultiResults = false;
        
        // Set the paraphrased result
        results.paraphrased = paraphrasedText;
        results.rewritten = '';
        results.final = '';

        try {
            const rewriteResponse = await fetch(`${API_BASE}/rewrite_only`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: paraphrasedText,
                    enhanced: useEnhanced
                })
            });

            if (rewriteResponse.ok) {
                const rewriteData = await rewriteResponse.json();
                results.rewritten = rewriteData.rewritten_text;
                results.final = rewriteData.rewritten_text;
                statistics = { 
                    ...rewriteData.statistics,
                    final_length: rewriteData.statistics.rewritten_length,
                    enhanced_rewriting_used: useEnhanced,
                    model_used: modelUsed,
                    original_length: inputText.length,
                    paraphrased_length: paraphrasedText.length
                };
                
                showToast('Text humanized successfully!');
            } else {
                const errorData = await rewriteResponse.json();
                throw new Error(errorData.error || 'Rewriting failed');
            }
        } catch (err) {
            logError('continueToRewrite', err, { useEnhanced });
            error = err.message;
            showToast(error, 'error');
        } finally {
            isProcessing = false;
            currentStep = 'complete';
        }
    }

    // Load available detection models
    async function loadDetectionModels() {
        try {
            const response = await fetch(`${API_BASE}/detect_models`);
            if (response.ok) {
                const data = await response.json();
                availableDetectionModels = data.available_models || [];
            } else {
                console.warn('Failed to load detection models');
            }
        } catch (err) {
            logError('loadDetectionModels', err);
            console.warn('Failed to load detection models:', err);
        }
    }

    // AI Detection Functions
    async function detectAIText(mode = 'ensemble') {
        if (!validateInput()) return;

        isDetecting = true;
        detectionResults = null;
        showDetectionResults = false;
        error = null;

        try {
            let endpoint = '';
            let requestBody = {
                text: inputText,
                threshold: detectionThreshold
            };

            switch (mode) {
                case 'simple':
                    endpoint = '/detect_simple';
                    break;
                case 'single':
                    endpoint = '/detect_single';
                    requestBody.model = selectedDetectionModel;
                    break;
                case 'segments':
                    endpoint = '/detect_segments';
                    requestBody.segment_length = segmentLength;
                    break;
                case 'ensemble':
                default:
                    endpoint = '/detect';
                    break;
            }

            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            if (response.ok) {
                detectionResults = await response.json();
                detectionResults.mode = mode;
                showDetectionResults = true;
                
                const prediction = detectionResults.prediction || (detectionResults.is_ai_generated ? 'AI-generated' : 'Human-written');
                showToast(`Detection complete: ${prediction}`);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || `Detection failed: ${response.status}`);
            }
        } catch (err) {
            logError('detectAIText', err, { mode, inputLength: inputText.length });
            error = err.message;
            showToast(error, 'error');
        } finally {
            isDetecting = false;
        }
    }

    // Humanize and check combined function
    async function humanizeAndCheck() {
        if (!validateInput()) return;

        isProcessing = true;
        currentStep = 'humanizing and checking';
        combinedResults = null;
        showCombinedResults = false;
        error = null;

        try {
            const response = await fetch(`${API_BASE}/humanize_and_check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: inputText,
                    paraphrasing: true,
                    enhanced: useEnhanced,
                    model: selectedModel,
                    detection_threshold: detectionThreshold
                })
            });

            if (response.ok) {
                combinedResults = await response.json();
                showCombinedResults = true;
                
                const improved = combinedResults.improvement.detection_improved;
                const reduction = combinedResults.improvement.ai_probability_reduction;
                showToast(`Processing complete! ${improved ? 'Detection improved' : 'No detection improvement'} (${(reduction * 100).toFixed(1)}% reduction)`);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || `Combined processing failed: ${response.status}`);
            }
        } catch (err) {
            logError('humanizeAndCheck', err, { inputLength: inputText.length });
            error = err.message;
            showToast(error, 'error');
        } finally {
            isProcessing = false;
            currentStep = 'complete';
        }
    }

    // Character count helper
    $: characterCount = inputText.length;
    $: wordCount = inputText.trim().split(/\s+/).filter(word => word.length > 0).length;

    onMount(() => {
        try {
            loadBackendInfo();
            loadDetectionModels();
        } catch (err) {
            logError('onMount', err);
        }
    });
</script>

<svelte:head>
    <title>AI Text Humanizer & Detector</title>
    <meta name="description" content="Transform AI-generated text into natural, human-like content and detect AI-generated text" />
</svelte:head>

<!-- Toast Notification -->
{#if showToastFlag}
    <div class="toast toast--{toastType}">
        <div class="toast__content">
            {toastMessage}
        </div>
    </div>
{/if}

<div class="app">
    <!-- Compact Header -->
    <header class="header">
        <div class="header__container">
            <h1 class="header__title">AI Text Humanizer & Detector</h1>
            {#if backendStatus}
                <div class="status" class:status--connected={backendStatus.status === 'healthy'}>
                    <span class="status__dot"></span>
                    {backendStatus.status === 'healthy' ? 'Connected' : 'Disconnected'}
                    {#if backendStatus.features?.device}
                        <span class="status__device">({backendStatus.features.device})</span>
                    {/if}
                </div>
            {/if}
        </div>
    </header>

    <main class="main">
        <div class="container">
            <!-- Input Section -->
            <section class="input-section">
                <div class="input-header">
                    <label class="input-label">Enter AI-generated text to humanize</label>
                    <div class="stats">
                        {characterCount} chars • {wordCount} words
                    </div>
                </div>
                
                <textarea
                    bind:value={inputText}
                    placeholder="Paste your AI-generated text here..."
                    class="textarea"
                    rows="6"
                    maxlength="5000"
                ></textarea>

                <!-- Configuration -->
                <div class="config">
                    <div class="config-row">
                        <label class="option">
                            <input type="checkbox" bind:checked={useEnhanced} />
                            <span class="option__text">
                                Enhanced rewriting
                                <small>Uses advanced prompts for better quality (slower)</small>
                            </span>
                        </label>

                        {#if availableModels.length > 1}
                            <div class="model-select">
                                <label class="model-select__label">Model:</label>
                                <select bind:value={selectedModel} class="model-select__dropdown">
                                    {#each availableModels as model}
                                        <option value={model}>{model}</option>
                                    {/each}
                                </select>
                            </div>
                        {/if}
                    </div>
                </div>

                <!-- AI Detection Controls -->
                <div class="detection-config">
                    <h3>AI Detection Settings</h3>
                    <div class="detection-row">
                        <div class="detection-option">
                            <label class="detection-label">Detection Mode:</label>
                            <select bind:value={detectionMode} class="detection-select">
                                <option value="ensemble">Ensemble (Multiple Models)</option>
                                <option value="simple">Simple Detection</option>
                                <option value="single">Single Model</option>
                                <option value="segments">Segment Analysis</option>
                            </select>
                        </div>

                        {#if detectionMode === 'single' && availableDetectionModels.length > 0}
                            <div class="detection-option">
                                <label class="detection-label">Model:</label>
                                <select bind:value={selectedDetectionModel} class="detection-select">
                                    {#each availableDetectionModels as model}
                                        <option value={model.name}>{model.description}</option>
                                    {/each}
                                </select>
                            </div>
                        {/if}

                        <div class="detection-option">
                            <label class="detection-label">Threshold:</label>
                            <input 
                                type="range" 
                                min="0.1" 
                                max="0.9" 
                                step="0.1" 
                                bind:value={detectionThreshold}
                                class="threshold-slider"
                            />
                            <span class="threshold-value">{detectionThreshold}</span>
                        </div>

                        {#if detectionMode === 'segments'}
                            <div class="detection-option">
                                <label class="detection-label">Segment Length:</label>
                                <input 
                                    type="number" 
                                    min="50" 
                                    max="1000" 
                                    step="50" 
                                    bind:value={segmentLength}
                                    class="segment-input"
                                />
                            </div>
                        {/if}
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="actions">
                    <!-- AI Detection Actions -->
                    <div class="action-group">
                        <h3>AI Detection</h3>
                        <div class="buttons">
                            <button 
                                class="btn btn--detection" 
                                on:click={() => detectAIText(detectionMode)} 
                                disabled={isDetecting || isProcessing || !inputText.trim()}
                            >
                                {#if isDetecting}
                                    <div class="spinner"></div>
                                    Detecting...
                                {:else}
                                    Detect AI Content
                                {/if}
                            </button>
                        </div>
                    </div>

                    <!-- Combined Processing -->
                    <div class="action-group">
                        <h3>Humanize & Verify</h3>
                        <div class="buttons">
                            <button 
                                class="btn btn--combined" 
                                on:click={humanizeAndCheck} 
                                disabled={isProcessing || isDetecting || !inputText.trim()}
                            >
                                {#if isProcessing && currentStep === 'humanizing and checking'}
                                    <div class="spinner"></div>
                                    Processing & Checking...
                                {:else}
                                    Humanize & Check Detection
                                {/if}
                            </button>
                        </div>
                    </div>

                    <div class="action-group">
                        <h3>Complete Pipeline (Paraphrase → Rewrite)</h3>
                        <div class="buttons">
                            <button 
                                class="btn btn--primary" 
                                on:click={humanizeWithSingleModel} 
                                disabled={isProcessing || !inputText.trim()}
                            >
                                {#if isProcessing && processingMode === 'single'}
                                    <div class="spinner"></div>
                                    {currentStep === 'paraphrasing' ? 'Paraphrasing...' : 
                                     currentStep === 'rewriting' ? 'Rewriting...' : 'Processing...'}
                                {:else}
                                    Humanize with {selectedModel || 'Current Model'}
                                {/if}
                            </button>
                        </div>
                    </div>

                    <div class="action-group">
                        <h3>Pipeline Processing (Dual/Multi Filter)</h3>
                        <div class="buttons">
                            <button 
                                class="btn btn--secondary" 
                                on:click={paraphraseWithMultiModels} 
                                disabled={isProcessing || !inputText.trim()}
                            >
                                {#if isProcessing && processingMode === 'multi'}
                                    <div class="spinner"></div>
                                    Pipeline processing...
                                {:else}
                                    2-Model Pipeline Filter
                                {/if}
                            </button>

                            <button 
                                class="btn btn--secondary" 
                                on:click={paraphraseWithAllModels} 
                                disabled={isProcessing || !inputText.trim()}
                            >
                                {#if isProcessing && processingMode === 'all'}
                                    <div class="spinner"></div>
                                    Full pipeline processing...
                                {:else}
                                    Full {availableModels.length}-Model Pipeline
                                {/if}
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Error Display -->
            {#if error}
                <div class="error">
                    <span class="error__icon">⚠</span>
                    {error}
                </div>
            {/if}

            <!-- AI Detection Results -->
            {#if showDetectionResults && detectionResults}
                <section class="results">
                    <h2 class="results__title">AI Detection Results</h2>
                    
                    <div class="detection-summary">
                        <div class="detection-main">
                            <div class="prediction-badge" class:ai-detected={detectionResults.is_ai_generated} class:human-detected={!detectionResults.is_ai_generated}>
                                {detectionResults.prediction || (detectionResults.is_ai_generated ? 'AI-Generated' : 'Human-Written')}
                            </div>
                            <div class="confidence-meter">
                                <div class="confidence-label">Confidence: {(detectionResults.confidence || detectionResults.ai_probability || 0).toFixed(3)}</div>
                                <div class="confidence-bar">
                                    <div 
                                        class="confidence-fill" 
                                        class:ai-confidence={detectionResults.is_ai_generated}
                                        style="width: {((detectionResults.confidence || detectionResults.ai_probability || 0) * 100)}%"
                                    ></div>
                                </div>
                            </div>
                        </div>

                        <div class="detection-stats">
                            {#if detectionResults.ai_probability !== undefined}
                                <span class="stat">AI: {(detectionResults.ai_probability * 100).toFixed(1)}%</span>
                            {/if}
                            {#if detectionResults.human_probability !== undefined}
                                <span class="stat">Human: {(detectionResults.human_probability * 100).toFixed(1)}%</span>
                            {/if}
                            <span class="stat">Mode: {detectionResults.mode}</span>
                            <span class="stat">Length: {detectionResults.text_length || inputText.length} chars</span>
                        </div>
                    </div>

                    <!-- Detailed Results based on mode -->
                    {#if detectionResults.mode === 'ensemble' && detectionResults.individual_results}
                        <div class="ensemble-details">
                            <h4>Individual Model Results</h4>
                            <div class="model-results">
                                {#each detectionResults.individual_results as result}
                                    <div class="model-result">
                                        <div class="model-name">{result.model_used}</div>
                                        <div class="model-prediction" class:ai-result={result.ai_probability > 0.5}>
                                            {(result.ai_probability * 100).toFixed(1)}% AI
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    {#if detectionResults.mode === 'segments' && detectionResults.segment_results}
                        <div class="segment-details">
                            <h4>Segment Analysis</h4>
                            <div class="segment-stats">
                                <span class="badge">Total: {detectionResults.total_segments}</span>
                                <span class="badge">Consistency: {(detectionResults.consistency * 100).toFixed(1)}%</span>
                                <span class="badge">Segment Length: {detectionResults.segment_length_used}</span>
                            </div>
                            <div class="segment-results">
                                {#each detectionResults.segment_results as segment, index}
                                    <div class="segment-item">
                                        <div class="segment-header">
                                            <span class="segment-number">#{index + 1}</span>
                                            <span class="segment-prediction" class:ai-segment={segment.is_ai_generated}>
                                                {segment.prediction} ({(segment.ai_probability * 100).toFixed(1)}%)
                                            </span>
                                        </div>
                                        <div class="segment-text">
                                            {segment.text.substring(0, 100)}...
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}
                </section>
            {/if}

            <!-- Combined Results -->
            {#if showCombinedResults && combinedResults}
                <section class="results">
                    <h2 class="results__title">Humanization & Detection Results</h2>
                    
                    <div class="combined-summary">
                        <div class="improvement-badge" class:improved={combinedResults.improvement.detection_improved} class:not-improved={!combinedResults.improvement.detection_improved}>
                            {combinedResults.improvement.detection_improved ? 'Detection Improved! ✓' : 'No Improvement ✗'}
                        </div>
                        
                        <div class="improvement-stats">
                            <span class="stat">Reduction: {(combinedResults.improvement.ai_probability_reduction * 100).toFixed(1)}%</span>
                            <span class="stat">Improvement: {combinedResults.improvement.percentage_improvement.toFixed(1)}%</span>
                        </div>
                    </div>

                    <div class="before-after">
                        <div class="detection-comparison">
                            <div class="before-detection">
                                <h4>Before Humanization</h4>
                                <div class="detection-result">
                                    <div class="prediction-small" class:ai-detected={combinedResults.original_detection.is_ai_generated}>
                                        {combinedResults.original_detection.prediction}
                                    </div>
                                    <div class="probability">AI: {(combinedResults.original_detection.ai_probability * 100).toFixed(1)}%</div>
                                </div>
                            </div>

                            <div class="after-detection">
                                <h4>After Humanization</h4>
                                <div class="detection-result">
                                    <div class="prediction-small" class:ai-detected={combinedResults.humanized_detection.is_ai_generated} class:human-detected={!combinedResults.humanized_detection.is_ai_generated}>
                                        {combinedResults.humanized_detection.prediction}
                                    </div>
                                    <div class="probability">AI: {(combinedResults.humanized_detection.ai_probability * 100).toFixed(1)}%</div>
                                </div>
                            </div>
                        </div>

                        <div class="text-comparison">
                            <div class="text-before">
                                <div class="text-header">
                                    <h4>Original Text</h4>
                                    <button class="copy-btn" on:click={() => copyToClipboard(combinedResults.original_text)}>
                                        Copy
                                    </button>
                                </div>
                                <div class="text-content">
                                    {combinedResults.original_text}
                                </div>
                            </div>

                            <div class="text-after">
                                <div class="text-header">
                                    <h4>Humanized Text</h4>
                                    <button class="copy-btn copy-btn--primary" on:click={() => copyToClipboard(combinedResults.humanized_text)}>
                                        Copy
                                    </button>
                                </div>
                                <div class="text-content">
                                    {combinedResults.humanized_text}
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            {/if}

            <!-- Pipeline Results -->
            {#if showMultiResults && (multiResults || allResults)}
                <section class="results">
                    <h2 class="results__title">
                        {multiResults ? '2-Model Pipeline Results' : 'Full Pipeline Results'}
                    </h2>
                    <p class="results__subtitle">
                        Pipeline mode: Each model processes the output of the previous model. 
                        Choose any step's output to continue with rewriting:
                    </p>
                    
                    {#if multiResults}
                        <div class="pipeline-summary">
                            <span class="badge badge--success">{multiResults.statistics.successful_steps} successful</span>
                            <span class="badge badge--error">{multiResults.statistics.failed_steps} failed</span>
                            <span class="badge">Length change: {multiResults.statistics.total_length_change}</span>
                            <span class="badge">Mode: {multiResults.statistics.pipeline_mode}</span>
                        </div>

                        <div class="pipeline-flow">
                            <div class="pipeline-step pipeline-step--original">
                                <div class="pipeline-step__header">
                                    <strong>Original Text</strong>
                                    <div class="pipeline-step__actions">
                                        <button class="copy-btn" on:click={() => copyToClipboard(multiResults.original_text)}>
                                            Copy
                                        </button>
                                        <button 
                                            class="btn btn--primary btn--small" 
                                            on:click={() => continueToRewrite(multiResults.original_text, 'original')}
                                            disabled={isProcessing}
                                        >
                                            Skip to Rewrite
                                        </button>
                                    </div>
                                </div>
                                <div class="pipeline-step__text">
                                    {multiResults.original_text}
                                </div>
                                <div class="pipeline-step__meta">
                                    {multiResults.statistics.original_length} chars
                                </div>
                            </div>

                            {#each multiResults.pipeline_results as result, index}
                                <div class="pipeline-arrow">↓ Model {result.step}: {result.model}</div>
                                
                                <div class="pipeline-step" class:pipeline-step--failed={!result.success} class:pipeline-step--final={index === multiResults.pipeline_results.length - 1}>
                                    <div class="pipeline-step__header">
                                        <strong>
                                            <span class="status-dot" class:success={result.success} class:failed={!result.success}></span>
                                            Step {result.step} Output
                                            {#if index === multiResults.pipeline_results.length - 1}
                                                <span class="final-badge">FINAL</span>
                                            {/if}
                                        </strong>
                                        {#if result.success}
                                            <div class="pipeline-step__actions">
                                                <button class="copy-btn" on:click={() => copyToClipboard(result.output_text)}>
                                                    Copy
                                                </button>
                                                <button 
                                                    class="btn btn--primary btn--small" 
                                                    on:click={() => continueToRewrite(result.output_text, result.model)}
                                                    disabled={isProcessing}
                                                >
                                                    Continue to Rewrite
                                                </button>
                                            </div>
                                        {/if}
                                    </div>
                                    <div class="pipeline-step__text">
                                        {result.output_text}
                                    </div>
                                    {#if result.success}
                                        <div class="pipeline-step__meta">
                                            {result.output_length} chars 
                                            <span class:positive={result.length_change > 0} class:negative={result.length_change < 0}>
                                                ({result.length_change > 0 ? '+' : ''}{result.length_change})
                                            </span>
                                        </div>
                                    {:else if result.error}
                                        <div class="pipeline-step__error">
                                            Error: {result.error}
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    {/if}

                    {#if allResults}
                        <div class="pipeline-summary">
                            <span class="badge badge--success">{allResults.statistics.successful_steps} successful</span>
                            <span class="badge badge--error">{allResults.statistics.failed_steps} failed</span>
                            <span class="badge">{allResults.statistics.total_processing_time}s total</span>
                            <span class="badge">Length change: {allResults.statistics.total_length_change}</span>
                            <span class="badge">Mode: {allResults.statistics.pipeline_mode}</span>
                        </div>

                        <div class="pipeline-flow">
                            <div class="pipeline-step pipeline-step--original">
                                <div class="pipeline-step__header">
                                    <strong>Original Text</strong>
                                    <div class="pipeline-step__actions">
                                        <button class="copy-btn" on:click={() => copyToClipboard(allResults.original_text)}>
                                            Copy
                                        </button>
                                        <button 
                                            class="btn btn--primary btn--small" 
                                            on:click={() => continueToRewrite(allResults.original_text, 'original')}
                                            disabled={isProcessing}
                                        >
                                            Skip to Rewrite
                                        </button>
                                    </div>
                                </div>
                                <div class="pipeline-step__text">
                                    {allResults.original_text}
                                </div>
                                <div class="pipeline-step__meta">
                                    {allResults.statistics.original_length} chars
                                </div>
                            </div>

                            {#each allResults.pipeline_results as result, index}
                                <div class="pipeline-arrow">
                                    ↓ Model {result.step}: {result.model}
                                    {#if result.processing_time}
                                        <small>({result.processing_time}s)</small>
                                    {/if}
                                </div>
                                
                                <div class="pipeline-step" class:pipeline-step--failed={!result.success} class:pipeline-step--final={index === allResults.pipeline_results.length - 1}>
                                    <div class="pipeline-step__header">
                                        <strong>
                                            <span class="status-dot" class:success={result.success} class:failed={!result.success}></span>
                                            Step {result.step} Output
                                            {#if index === allResults.pipeline_results.length - 1}
                                                <span class="final-badge">FINAL</span>
                                            {/if}
                                        </strong>
                                        {#if result.success}
                                            <div class="pipeline-step__actions">
                                                <button class="copy-btn" on:click={() => copyToClipboard(result.output_text)}>
                                                    Copy
                                                </button>
                                                <button 
                                                    class="btn btn--primary btn--small" 
                                                    on:click={() => continueToRewrite(result.output_text, result.model)}
                                                    disabled={isProcessing}
                                                >
                                                    Continue to Rewrite
                                                </button>
                                            </div>
                                        {/if}
                                    </div>
                                    <div class="pipeline-step__text">
                                        {result.output_text}
                                    </div>
                                    {#if result.success}
                                        <div class="pipeline-step__meta">
                                            {result.output_length} chars 
                                            <span class:positive={result.length_change > 0} class:negative={result.length_change < 0}>
                                                ({result.length_change > 0 ? '+' : ''}{result.length_change})
                                            </span>
                                        </div>
                                    {:else if result.error}
                                        <div class="pipeline-step__error">
                                            Error: {result.error}
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    {/if}
                </section>
            {/if}

            <!-- Single Pipeline Result -->
            {#if results.final && !showMultiResults}
                <section class="results">
                    <h2 class="results__title">Humanized Text</h2>
                    
                    <!-- Show both steps -->
                    <div class="pipeline-results">
                        {#if results.paraphrased}
                            <div class="step-result">
                                <div class="step-result__header">
                                    <h3>Step 1: Paraphrased</h3>
                                    <button class="copy-btn" on:click={() => copyToClipboard(results.paraphrased)}>
                                        Copy
                                    </button>
                                </div>
                                <div class="step-result__text">
                                    {results.paraphrased}
                                </div>
                            </div>
                        {/if}

                        <div class="step-result step-result--final">
                            <div class="step-result__header">
                                <h3>Step 2: Final Humanized Text</h3>
                                <button class="copy-btn copy-btn--primary" on:click={() => copyToClipboard(results.final)}>
                                    Copy Final
                                </button>
                            </div>
                            <div class="step-result__text">
                                {results.final}
                            </div>
                            
                            {#if statistics && Object.keys(statistics).length > 0}
                                <div class="quick-stats">
                                    <span>
                                        {statistics.original_length || 0} → {statistics.paraphrased_length || 0} → {statistics.final_length || statistics.rewritten_length || 0} chars
                                    </span>
                                    {#if statistics.model_used}
                                        <span>• Model: {statistics.model_used}</span>
                                    {/if}
                                    {#if statistics.enhanced_rewriting_used}
                                        <span>• Enhanced rewriting</span>
                                    {/if}
                                </div>
                            {/if}
                        </div>
                    </div>
                </section>
            {/if}
        </div>
    </main>
</div>

<style>
    /* Reset and base styles */
    :global(*) {
        box-sizing: border-box;
    }

    :global(body) {
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        line-height: 1.5;
        color: #1f2937;
        background: #f8fafc;
    }

    /* Layout */
    .app {
        min-height: 100vh;
    }

    /* Compact Header */
    .header {
        background: white;
        border-bottom: 1px solid #e5e7eb;
        padding: 1rem 0;
    }

    .header__container {
        max-width: 800px;
        margin: 0 auto;
        padding: 0 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .header__title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1f2937;
        margin: 0;
    }

    .status {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        color: #6b7280;
    }

    .status__dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #ef4444;
    }

    .status--connected .status__dot {
        background: #10b981;
    }

    .status__device {
        font-size: 0.75rem;
        opacity: 0.7;
    }

    .main {
        padding: 2rem 0;
    }

    .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 0 1rem;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    /* Input Section */
    .input-section {
        background: white;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
    }

    .input-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }

    .input-label {
        font-weight: 600;
        color: #1f2937;
    }

    .stats {
        font-size: 0.875rem;
        color: #6b7280;
    }

    .textarea {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        font-size: 0.875rem;
        font-family: inherit;
        resize: vertical;
        margin-bottom: 1rem;
    }

    .textarea:focus {
        outline: none;
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }

    /* Options */
    .options {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }

    .options__group {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .option {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        cursor: pointer;
    }

    .option input {
        margin-top: 0.125rem;
    }

    .option__text {
        display: flex;
        flex-direction: column;
    }

    .option__text small {
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 0.125rem;
    }

    .model-select {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
    }

    .model-select__label {
        color: #6b7280;
        white-space: nowrap;
    }

    .model-select__dropdown {
        padding: 0.25rem 0.5rem;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        font-size: 0.875rem;
    }

    /* Actions */
    .actions {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
    }

    .btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .btn--primary {
        background: #3b82f6;
        color: white;
    }

    .btn--primary:hover:not(:disabled) {
        background: #2563eb;
        transform: translateY(-1px);
    }

    .btn--secondary {
        background: #f3f4f6;
        color: #374151;
        border: 1px solid #d1d5db;
    }

    .btn--secondary:hover:not(:disabled) {
        background: #e5e7eb;
    }

    .btn--detection {
        background: #0ea5e9;
        color: white;
    }

    .btn--detection:hover:not(:disabled) {
        background: #0284c7;
    }

    .btn--combined {
        background: #8b5cf6;
        color: white;
    }

    .btn--combined:hover:not(:disabled) {
        background: #7c3aed;
    }

    .spinner {
        width: 1rem;
        height: 1rem;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top: 2px solid currentColor;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    /* Error */
    .error {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: #fef2f2;
        border: 1px solid #fecaca;
        color: #991b1b;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-size: 0.875rem;
    }

    .error__icon {
        flex-shrink: 0;
    }

    /* Results */
    .results {
        background: white;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
    }

    .results__title {
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0 0 1rem 0;
    }

    /* Final Result */
    .final-result {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
    }

    .final-result__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
    }

    .final-result__text {
        padding: 1rem;
        line-height: 1.6;
        white-space: pre-wrap;
    }

    .copy-btn {
        padding: 0.375rem 0.75rem;
        background: transparent;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        font-size: 0.75rem;
        cursor: pointer;
        color: #6b7280;
    }

    .copy-btn:hover {
        background: #f3f4f6;
    }

    .copy-btn--primary {
        background: #3b82f6;
        color: white;
        border-color: #3b82f6;
    }

    .copy-btn--primary:hover {
        background: #2563eb;
    }

    .quick-stats {
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-top: 1px solid #e5e7eb;
        font-size: 0.875rem;
        color: #6b7280;
    }

    /* Processing Steps */
    .steps {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }

    .steps summary {
        cursor: pointer;
        font-size: 0.875rem;
        color: #6b7280;
        margin-bottom: 0.75rem;
    }

    .step {
        background: #f9fafb;
        border-radius: 6px;
        padding: 0.75rem;
    }

    .step h4 {
        margin: 0 0 0.5rem 0;
        font-size: 0.875rem;
        font-weight: 600;
    }

    .step__text {
        font-size: 0.875rem;
        line-height: 1.5;
        white-space: pre-wrap;
    }

    /* Comparison Grid */
    .results-summary {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }

    .badge {
        padding: 0.25rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        background: #f3f4f6;
        color: #374151;
    }

    .badge--success {
        background: #dcfce7;
        color: #166534;
    }

    .badge--error {
        background: #fef2f2;
        color: #991b1b;
    }

    .comparison-grid {
        display: grid;
        gap: 1rem;
    }

    .result {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
    }

    .result--failed {
        border-color: #fecaca;
        background: #fef2f2;
    }

    .result__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
    }

    .result--failed .result__header {
        background: #fef2f2;
        border-color: #fecaca;
    }

    .result__text {
        padding: 1rem;
        line-height: 1.5;
        font-size: 0.875rem;
        white-space: pre-wrap;
    }

    .result__meta {
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-top: 1px solid #e5e7eb;
        font-size: 0.75rem;
        color: #6b7280;
    }

    .result__error {
        padding: 0.75rem 1rem;
        background: #fef2f2;
        border-top: 1px solid #fecaca;
        font-size: 0.75rem;
        color: #dc2626;
    }

    .status-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 0.375rem;
    }

    .status-dot.success {
        background: #10b981;
    }

    .status-dot.failed {
        background: #ef4444;
    }

    .positive {
        color: #059669;
    }

    .negative {
        color: #dc2626;
    }

    /* Toast */
    .toast {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 50;
        max-width: 20rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        animation: slideIn 0.3s ease-out;
    }

    .toast--success {
        background: #10b981;
    }

    .toast--error {
        background: #ef4444;
    }

    .toast__content {
        padding: 0.75rem 1rem;
        color: white;
        font-size: 0.875rem;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    /* Responsive */
    @media (max-width: 640px) {
        .header__container {
            flex-direction: column;
            gap: 0.5rem;
        }

        .options {
            flex-direction: column;
            align-items: flex-start;
        }

        .actions {
            flex-direction: column;
        }

        .btn {
            width: 100%;
            justify-content: center;
        }

        .final-result__header,
        .result__header {
            flex-direction: column;
            gap: 0.5rem;
            align-items: flex-start;
        }
    }

    /* Action Groups */
    .action-group {
        margin-bottom: 1.5rem;
    }

    .action-group:last-child {
        margin-bottom: 0;
    }

    .action-group h3 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.75rem 0;
        color: #374151;
    }

    .buttons {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    /* Configuration */
    .config {
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: #f9fafb;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
    }

    .config-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        flex-wrap: wrap;
    }

    /* AI Detection Styles */
    .detection-config {
        margin-top: 1rem;
        padding: 1rem;
        background: #f0f9ff;
        border-radius: 8px;
        border: 1px solid #e0f2fe;
    }

    .detection-config h3 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.75rem 0;
        color: #0c4a6e;
    }

    .detection-row {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: center;
    }

    .detection-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .detection-label {
        font-size: 0.875rem;
        color: #374151;
        white-space: nowrap;
    }

    .detection-select {
        padding: 0.375rem 0.75rem;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        font-size: 0.875rem;
        background: white;
    }

    .threshold-slider {
        width: 100px;
    }

    .threshold-value {
        font-size: 0.875rem;
        font-weight: 600;
        color: #1f2937;
        min-width: 2rem;
        text-align: center;
    }

    .segment-input {
        width: 80px;
        padding: 0.375rem 0.5rem;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        font-size: 0.875rem;
    }

    /* Detection Results */
    .detection-summary {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .detection-main {
        display: flex;
        align-items: center;
        gap: 1.5rem;
        flex-wrap: wrap;
    }

    .prediction-badge {
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1.125rem;
        text-align: center;
    }

    .prediction-badge.ai-detected {
        background: #fef2f2;
        color: #991b1b;
        border: 2px solid #fecaca;
    }

    .prediction-badge.human-detected {
        background: #f0fdf4;
        color: #166534;
        border: 2px solid #bbf7d0;
    }

    .confidence-meter {
        flex: 1;
        min-width: 200px;
    }

    .confidence-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-bottom: 0.5rem;
    }

    .confidence-bar {
        width: 100%;
        height: 8px;
        background: #e5e7eb;
        border-radius: 4px;
        overflow: hidden;
    }

    .confidence-fill {
        height: 100%;
        background: #10b981;
        transition: width 0.3s ease;
    }

    .confidence-fill.ai-confidence {
        background: #ef4444;
    }

    .detection-stats {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .stat {
        padding: 0.25rem 0.75rem;
        background: #f3f4f6;
        border-radius: 12px;
        font-size: 0.875rem;
        color: #374151;
    }

    /* Ensemble Results */
    .ensemble-details {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }

    .ensemble-details h4 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.75rem 0;
        color: #374151;
    }

    .model-results {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.75rem;
    }

    .model-result {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        background: #f9fafb;
        border-radius: 6px;
        border: 1px solid #e5e7eb;
    }

    .model-name {
        font-size: 0.875rem;
        color: #374151;
        font-weight: 500;
    }

    .model-prediction {
        font-size: 0.875rem;
        font-weight: 600;
        color: #10b981;
    }

    .model-prediction.ai-result {
        color: #ef4444;
    }

    /* Segment Results */
    .segment-details {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e5e7eb;
    }

    .segment-details h4 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.75rem 0;
        color: #374151;
    }

    .segment-stats {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }

    .segment-results {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
    }

    .segment-item {
        border-bottom: 1px solid #e5e7eb;
        padding: 0.75rem;
    }

    .segment-item:last-child {
        border-bottom: none;
    }

    .segment-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .segment-number {
        font-size: 0.75rem;
        color: #6b7280;
        font-weight: 600;
    }

    .segment-prediction {
        font-size: 0.875rem;
        font-weight: 500;
        color: #10b981;
    }

    .segment-prediction.ai-segment {
        color: #ef4444;
    }

    .segment-text {
        font-size: 0.875rem;
        color: #6b7280;
        line-height: 1.4;
    }

    /* Combined Results */
    .combined-summary {
        display: flex;
        align-items: center;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }

    .improvement-badge {
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1.125rem;
    }

    .improvement-badge.improved {
        background: #f0fdf4;
        color: #166534;
        border: 2px solid #bbf7d0;
    }

    .improvement-badge.not-improved {
        background: #fef2f2;
        color: #991b1b;
        border: 2px solid #fecaca;
    }

    .improvement-stats {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .before-after {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .detection-comparison {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .before-detection,
    .after-detection {
        padding: 1rem;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #f9fafb;
    }

    .before-detection h4,
    .after-detection h4 {
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0 0 0.75rem 0;
        color: #374151;
    }

    .detection-result {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .prediction-small {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
        font-size: 0.875rem;
    }

    .prediction-small.ai-detected {
        background: #fecaca;
        color: #991b1b;
    }

    .prediction-small.human-detected {
        background: #bbf7d0;
        color: #166534;
    }

    .probability {
        font-size: 0.875rem;
        color: #6b7280;
        text-align: center;
    }

    .text-comparison {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .text-before,
    .text-after {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
    }

    .text-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
    }

    .text-header h4 {
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0;
        color: #374151;
    }

    .text-content {
        padding: 1rem;
        line-height: 1.6;
        font-size: 0.875rem;
        white-space: pre-wrap;
        max-height: 300px;
        overflow-y: auto;
    }

    /* Processing Flow */
    .pipeline-flow {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 1rem;
    }

    .pipeline-step {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
        background: white;
    }

    .pipeline-step--original {
        border-color: #6b7280;
        background: #f9fafb;
    }

    .pipeline-step--final {
        border-color: #10b981;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.1);
    }

    .pipeline-step--failed {
        border-color: #fecaca;
        background: #fef2f2;
    }

    .pipeline-step__header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
    }

    .pipeline-step--final .pipeline-step__header {
        background: #ecfdf5;
        border-color: #d1fae5;
    }

    .pipeline-step--failed .pipeline-step__header {
        background: #fef2f2;
        border-color: #fecaca;
    }

    .pipeline-step__text {
        padding: 1rem;
        line-height: 1.5;
        font-size: 0.875rem;
        white-space: pre-wrap;
    }

    .pipeline-step__meta {
        padding: 0.75rem 1rem;
        background: #f9fafb;
        border-top: 1px solid #e5e7eb;
        font-size: 0.75rem;
        color: #6b7280;
    }

    .pipeline-step__error {
        padding: 0.75rem 1rem;
        background: #fef2f2;
        border-top: 1px solid #fecaca;
        font-size: 0.75rem;
        color: #dc2626;
    }

    .pipeline-arrow {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.5rem;
        color: #6b7280;
        font-size: 0.875rem;
        font-weight: 500;
        background: #f9fafb;
        border-radius: 4px;
        margin: 0.25rem 2rem;
        text-align: center;
    }

    .pipeline-arrow small {
        font-weight: normal;
        opacity: 0.7;
    }

    .pipeline-summary {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }

    .final-badge {
        background: #10b981;
        color: white;
        padding: 0.125rem 0.375rem;
        border-radius: 12px;
        font-size: 0.625rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }

    /* Responsive adjustments */
    @media (max-width: 640px) {
        .config-row {
            flex-direction: column;
            align-items: flex-start;
        }

        .buttons {
            flex-direction: column;
        }

        .btn {
            width: 100%;
            justify-content: center;
        }

        .result__header {
            flex-direction: column;
            gap: 0.75rem;
            align-items: flex-start;
        }

        .result__actions {
            width: 100%;
            justify-content: space-between;
        }

        .detection-row {
            flex-direction: column;
            align-items: flex-start;
        }

        .detection-comparison,
        .text-comparison {
            grid-template-columns: 1fr;
        }

        .detection-main {
            flex-direction: column;
            align-items: flex-start;
        }

        .combined-summary {
            flex-direction: column;
            align-items: flex-start;
        }
    }
</style>