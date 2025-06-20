<script>
    import { onMount } from 'svelte';
    import { derived } from 'svelte/store';
    import '$lib/style.css';
    
    // Import all the stores and functions from the external script
    import {
        // Stores
        inputText, isProcessing, currentStep, error, results, statistics,
        multiResults, allResults, showMultiResults, availableModels, currentModel,
        selectedModel, useEnhanced, backendStatus, processingMode,
        detectionResults, isDetecting, detectionMode, selectedDetectionModel,
        detectionThreshold, segmentLength, availableDetectionModels,
        showDetectionResults, combinedResults, showCombinedResults,
        toastMessage, toastType, showToastFlag,
        
        // Enhanced AI Detection features
        lineDetectionResults, sentenceDetectionResults, highlightedText,
        detectionFormat, useAllDetectionModels, topNModels, detectionCriteria,
        minLineLength,
        
        // Functions
        copyToClipboard, loadBackendInfo, humanizeWithSingleModel,
        paraphraseWithMultiModels, paraphraseWithAllModels, continueToRewrite,
        loadDetectionModels, detectAIText, humanizeAndCheck,
        
        // Enhanced detection functions
        detectAILines, detectAISentences, highlightAIText,
        detectWithAllModels, detectWithSelectedModels, detectWithTopModels,
        getDetectionModelInfo, getRecommendedDetectionModel,
        
        // Add the missing function
        validateDetectionInput, getAILines, showToast
    } from '$lib/script.js';

    // New stores for enhanced configuration
    import { writable } from 'svelte/store';
    const selectedDetectionModels = writable([]);
    const showAdvancedConfig = writable(false);
    const showDetectionHelp = writable(false);
    const showHumanizationHelp = writable(false);

    // Add new store for AI lines backup display
    const aiLinesSimple = writable([]);
    const showAILines = writable(false);

    // Derived stores for computed values
    const characterCount = derived(inputText, $inputText => $inputText.length);
    const wordCount = derived(inputText, $inputText => 
        $inputText.trim().split(/\s+/).filter(word => word.length > 0).length
    );

    // Get detection model info
    const detectionModelInfo = getDetectionModelInfo();

    // Handler functions that pass the reactive values to the imported functions
    const handleHumanizeWithSingleModel = () => {
        humanizeWithSingleModel($inputText, $selectedModel, $useEnhanced);
    };

    const handleParaphraseWithMultiModels = () => {
        paraphraseWithMultiModels($inputText);
    };

    const handleParaphraseWithAllModels = () => {
        paraphraseWithAllModels($inputText);
    };

    const handleDetectAIText = () => {
        const options = {
            selectedModel: $selectedDetectionModel,
            segmentLength: $segmentLength,
            useAllModels: $useAllDetectionModels,
            topN: $topNModels,
            criteria: $detectionCriteria,
            selectedModels: $detectionMode === 'selected' ? $selectedDetectionModels : 
                           $useAllDetectionModels ? $availableDetectionModels.map(m => m.name) : 
                           [$selectedDetectionModel]
        };
        detectAIText($inputText, $detectionMode, $detectionThreshold, options);
    };

    const handleDetectAILines = () => {
        detectAILines($inputText, $detectionThreshold, $minLineLength);
    };

    const handleDetectAISentences = () => {
        detectAISentences($inputText, $detectionThreshold);
    };

    const handleHighlightAIText = () => {
        highlightAIText($inputText, $detectionThreshold, $detectionFormat);
    };

    const handleDetectWithAllModels = () => {
        detectWithAllModels($inputText, $detectionThreshold);
    };

    const handleDetectWithTopModels = () => {
        detectWithTopModels($inputText, $topNModels, $detectionCriteria, $detectionThreshold);
    };

    const handleHumanizeAndCheck = () => {
        humanizeAndCheck($inputText, $useEnhanced, $selectedModel, $detectionThreshold);
    };

    const handleContinueToRewrite = (paraphrasedText, modelUsed = null) => {
        continueToRewrite(paraphrasedText, modelUsed, $useEnhanced, $inputText);
    };

    // Toggle detection model selection
    const toggleDetectionModel = (modelName) => {
        selectedDetectionModels.update(models => {
            if (models.includes(modelName)) {
                return models.filter(m => m !== modelName);
            } else {
                return [...models, modelName];
            }
        });
    };

    // Set recommended detection models
    const setRecommendedModels = (criteria) => {
        const recommended = getRecommendedDetectionModel(criteria);
        selectedDetectionModels.set([recommended]);
    };

    // Add handler for getting AI lines as backup
    const handleGetAILines = async () => {
        if (!validateDetectionInput($inputText)) return;
        
        isDetecting.set(true);
        error.set(null);
        
        try {
            const lines = await getAILines($inputText, $detectionThreshold);
            // Fix: Ensure we're extracting the text content from objects
            const processedLines = lines.map(line => {
                if (typeof line === 'object' && line !== null) {
                    return line.text || line.content || String(line);
                }
                return String(line);
            });
            
            aiLinesSimple.set(processedLines);
            showAILines.set(true);
            showToast(`Found ${processedLines.length} AI-generated lines`);
        } catch (err) {
            error.set(err.message);
            showToast(err.message, 'error');
        } finally {
            isDetecting.set(false);
        }
    };

    onMount(() => {
        try {
            loadBackendInfo();
            loadDetectionModels();
            // Set default selected detection model
            selectedDetectionModels.set([getRecommendedDetectionModel('performance')]);
        } catch (err) {
            console.error('Failed to initialize:', err);
        }
    });
</script>

<svelte:head>
    <title>AI Text Humanizer & Detector</title>
    <meta name="description" content="Transform AI-generated text into natural, human-like content and detect AI-generated text" />
</svelte:head>

<!-- Toast Notification -->
{#if $showToastFlag}
    <div class="toast toast--{$toastType}">
        <div class="toast__content">
            {$toastMessage}
        </div>
    </div>
{/if}

<div class="app">
    <!-- Compact Header -->
    <header class="header">
        <div class="header__container">
            <h1 class="header__title">AI Text Humanizer & Detector</h1>
            {#if $backendStatus}
                <div class="status" class:status--connected={$backendStatus.status === 'healthy'}>
                    <span class="status__dot"></span>
                    {$backendStatus.status === 'healthy' ? 'Connected' : 'Disconnected'}
                    {#if $backendStatus.features?.device}
                        <span class="status__device">({$backendStatus.features.device})</span>
                    {/if}
                </div>
            {/if}
        </div>
    </header>

    <main class="main">
        <div class="main-container">
            <!-- Enhanced Left Sidebar (35%) -->
            <aside class="sidebar">
                <!-- Humanization Configuration -->
                <section class="sidebar-section">
                    <div class="section-header">
                        <h3 class="sidebar-title">
                            Humanization Settings
                            <button 
                                class="help-btn" 
                                on:click={() => showHumanizationHelp.update(v => !v)}
                                title="Show help"
                            >
                                ?
                            </button>
                        </h3>
                    </div>

                    {#if $showHumanizationHelp}
                        <div class="help-panel">
                            <h4>How Humanization Works:</h4>
                            <ul class="help-list">
                                <li><strong>Step 1:</strong> Paraphrasing - Restructures sentences while keeping meaning</li>
                                <li><strong>Step 2:</strong> Rewriting - Applies human-like patterns and styles</li>
                                <li><strong>Enhanced:</strong> Uses advanced prompts for better quality (slower)</li>
                                <li><strong>Pipeline:</strong> Multiple models process text sequentially</li>
                            </ul>
                        </div>
                    {/if}
                    
                    <div class="config-option">
                        <label class="option">
                            <input type="checkbox" bind:checked={$useEnhanced} />
                            <span class="option__text">
                                Enhanced Rewriting
                                <small class="option__description">
                                    Uses advanced prompts with better context understanding. 
                                    Slower but produces more natural, human-like text.
                                </small>
                            </span>
                        </label>
                    </div>

                    {#if $availableModels.length > 1}
                        <div class="config-option">
                            <label class="config-label">
                                Humanization Model:
                                <small class="config-description">
                                    Model used for text transformation. Different models have varying writing styles.
                                </small>
                            </label>
                            <select bind:value={$selectedModel} class="config-select">
                                {#each $availableModels as model}
                                    <option value={model}>
                                        {model} {model === $currentModel ? '(loaded)' : ''}
                                    </option>
                                {/each}
                            </select>
                        </div>
                    {/if}
                </section>

                <!-- Enhanced AI Detection Settings -->
                <section class="sidebar-section">
                    <div class="section-header">
                        <h3 class="sidebar-title">
                            AI Detection Settings
                            <button 
                                class="help-btn" 
                                on:click={() => showDetectionHelp.update(v => !v)}
                                title="Show help"
                            >
                                ?
                            </button>
                        </h3>
                    </div>

                    {#if $showDetectionHelp}
                        <div class="help-panel">
                            <h4>Detection Modes Explained:</h4>
                            <ul class="help-list">
                                <li><strong>Ensemble:</strong> Combines multiple models for better accuracy</li>
                                <li><strong>Single Model:</strong> Uses one specific detection model</li>
                                <li><strong>All Models:</strong> Runs all available models and shows individual results</li>
                                <li><strong>Top N Models:</strong> Uses the best performing models based on criteria</li>
                                <li><strong>Line Analysis:</strong> Analyzes text line by line</li>
                                <li><strong>Sentence Analysis:</strong> Analyzes text sentence by sentence</li>
                            </ul>
                        </div>
                    {/if}
                    
                    <div class="config-option">
                        <label class="config-label">
                            Detection Mode:
                            <small class="config-description">
                                How AI detection is performed. Ensemble is recommended for best accuracy.
                            </small>
                        </label>
                        <select bind:value={$detectionMode} class="config-select">
                            <option value="ensemble">🎯 Ensemble Detection (Recommended)</option>
                            <option value="single">🔍 Single Model Detection</option>
                            <option value="all_models">📊 All Models Comparison</option>
                            <option value="selected">✅ Selected Models Only</option>
                            <option value="top_models">⭐ Top N Models</option>
                            <option value="segments">📝 Segment Analysis</option>
                        </select>
                    </div>

                    <!-- Detection Model Selection -->
                    {#if $detectionMode === 'single'}
                        <div class="config-option">
                            <label class="config-label">
                                Detection Model:
                                <small class="config-description">
                                    Choose a specific model for detection. Different models excel at different text types.
                                </small>
                            </label>
                            <select bind:value={$selectedDetectionModel} class="config-select">
                                {#each $availableDetectionModels as model}
                                    <option value={model.name}>
                                        {detectionModelInfo[model.name]?.name || model.name}
                                    </option>
                                {/each}
                            </select>
                            
                            {#if detectionModelInfo[$selectedDetectionModel]}
                                <div class="model-info">
                                    <div class="model-info__row">
                                        <span class="model-info__label">Type:</span>
                                        <span class="model-info__value">{detectionModelInfo[$selectedDetectionModel].type}</span>
                                    </div>
                                    <div class="model-info__row">
                                        <span class="model-info__label">Speed:</span>
                                        <span class="model-info__value">{detectionModelInfo[$selectedDetectionModel].speed}</span>
                                    </div>
                                    <div class="model-info__row">
                                        <span class="model-info__label">Accuracy:</span>
                                        <span class="model-info__value">{detectionModelInfo[$selectedDetectionModel].accuracy}</span>
                                    </div>
                                    <div class="model-description">
                                        {detectionModelInfo[$selectedDetectionModel].description}
                                    </div>
                                </div>
                            {/if}
                        </div>
                    {/if}

                    <!-- Selected Models Configuration -->
                    {#if $detectionMode === 'selected'}
                        <div class="config-option">
                            <label class="config-label">
                                Select Detection Models:
                                <small class="config-description">
                                    Choose specific models to use. More models = better accuracy but slower processing.
                                </small>
                            </label>
                            
                            <div class="model-selection">
                                <div class="quick-select">
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedModels('performance')}
                                    >
                                        Best Performance
                                    </button>
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedModels('speed')}
                                    >
                                        Fastest
                                    </button>
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedModels('accuracy')}
                                    >
                                        Most Accurate
                                    </button>
                                </div>

                                <div class="model-checkboxes">
                                    {#each $availableDetectionModels as model}
                                        <label class="model-checkbox">
                                            <input 
                                                type="checkbox" 
                                                checked={$selectedDetectionModels.includes(model.name)}
                                                on:change={() => toggleDetectionModel(model.name)}
                                            />
                                            <div class="model-checkbox__content">
                                                <div class="model-checkbox__name">
                                                    {detectionModelInfo[model.name]?.name || model.name}
                                                </div>
                                                <div class="model-checkbox__meta">
                                                    <span class="model-type">{detectionModelInfo[model.name]?.type}</span>
                                                    <span class="model-speed">Speed: {detectionModelInfo[model.name]?.speed}</span>
                                                    <span class="model-accuracy">Acc: {detectionModelInfo[model.name]?.accuracy}</span>
                                                </div>
                                                <div class="model-checkbox__description">
                                                    {detectionModelInfo[model.name]?.description}
                                                </div>
                                            </div>
                                        </label>
                                    {/each}
                                </div>
                                
                                <div class="selection-summary">
                                    Selected: {$selectedDetectionModels.length} models
                                </div>
                            </div>
                        </div>
                    {/if}

                    <!-- Top N Models Configuration -->
                    {#if $detectionMode === 'top_models'}
                        <div class="config-option">
                            <label class="config-label">
                                Number of Top Models:
                                <small class="config-description">
                                    How many best-performing models to use (1-5).
                                </small>
                            </label>
                            <input 
                                type="number" 
                                min="1" 
                                max="5" 
                                bind:value={$topNModels}
                                class="config-input"
                            />
                        </div>
                        <div class="config-option">
                            <label class="config-label">
                                Selection Criteria:
                                <small class="config-description">
                                    How to rank and select the top models.
                                </small>
                            </label>
                            <select bind:value={$detectionCriteria} class="config-select">
                                <option value="performance">🏆 Best Overall Performance</option>
                                <option value="speed">⚡ Fastest Processing</option>
                                <option value="accuracy">🎯 Highest Accuracy</option>
                            </select>
                        </div>
                    {/if}

                    <!-- Threshold Configuration -->
                    <div class="config-option">
                        <label class="config-label">
                            Detection Threshold: {$detectionThreshold}
                            <small class="config-description">
                                Sensitivity level. Higher = stricter (fewer false positives), Lower = more sensitive (catches more AI text).
                            </small>
                        </label>
                        <div class="threshold-container">
                            <input 
                                type="range" 
                                min="0.1" 
                                max="0.9" 
                                step="0.1" 
                                bind:value={$detectionThreshold}
                                class="threshold-slider"
                            />
                            <div class="threshold-labels">
                                <span class="threshold-label threshold-label--left">More Sensitive</span>
                                <span class="threshold-label threshold-label--right">More Strict</span>
                            </div>
                        </div>
                    </div>

                    <!-- Advanced Options -->
                    <div class="config-option">
                        <button 
                            class="btn btn--text btn--small" 
                            on:click={() => showAdvancedConfig.update(v => !v)}
                        >
                            {$showAdvancedConfig ? '▼' : '▶'} Advanced Options
                        </button>
                    </div>

                    {#if $showAdvancedConfig}
                        <div class="advanced-config">
                            {#if $detectionMode === 'segments'}
                                <div class="config-option">
                                    <label class="config-label">
                                        Segment Length:
                                        <small class="config-description">
                                            Text chunk size for analysis (50-1000 characters).
                                        </small>
                                    </label>
                                    <input 
                                        type="number" 
                                        min="50" 
                                        max="1000" 
                                        step="50" 
                                        bind:value={$segmentLength}
                                        class="config-input"
                                    />
                                </div>
                            {/if}

                            <div class="config-option">
                                <label class="config-label">
                                    Line Detection Min Length:
                                    <small class="config-description">
                                        Minimum line length for line-by-line analysis.
                                    </small>
                                </label>
                                <input 
                                    type="number" 
                                    min="10" 
                                    max="100" 
                                    bind:value={$minLineLength}
                                    class="config-input"
                                />
                            </div>

                            <div class="config-option">
                                <label class="config-label">
                                    Highlight Format:
                                    <small class="config-description">
                                        Output format for AI text highlighting.
                                    </small>
                                </label>
                                <select bind:value={$detectionFormat} class="config-select">
                                    <option value="markdown">📝 Markdown (** bold **)</option>
                                    <option value="html">🌐 HTML (&lt;mark&gt; tags)</option>
                                    <option value="plain">📄 Plain Text (brackets)</option>
                                </select>
                            </div>
                        </div>
                    {/if}
                </section>

                <!-- Enhanced Action Buttons with Clear Descriptions -->
                <section class="sidebar-section">
                    <h3 class="sidebar-title">Actions</h3>
                    
                    <!-- AI Detection Actions -->
                    <div class="action-group">
                        <h4 class="action-title">
                            🔍 AI Detection
                            <small class="action-description">Analyze text to detect AI-generated content</small>
                        </h4>
                        <div class="action-buttons">
                            <button 
                                class="btn btn--detection btn--full" 
                                on:click={handleDetectAIText} 
                                disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                                title="Detect AI content using configured settings"
                            >
                                {#if $isDetecting}
                                    <div class="spinner"></div>
                                    Detecting...
                                {:else}
                                    🎯 Smart Detection
                                {/if}
                            </button>
                            <div class="button-description">
                                Uses your configured detection mode and models to analyze the text.
                            </div>

                            <button 
                                class="btn btn--detection btn--full" 
                                on:click={handleDetectWithAllModels} 
                                disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                                title="Run detection with all available models for comparison"
                            >
                                📊 Compare All Models
                            </button>
                            <div class="button-description">
                                Runs all {$availableDetectionModels.length} detection models and shows individual results.
                            </div>
                        </div>
                    </div>

                    <!-- Advanced Detection -->
                    <div class="action-group">
                        <h4 class="action-title">
                            🔬 Advanced Analysis
                            <small class="action-description">Detailed text analysis with granular results</small>
                        </h4>
                        <div class="action-buttons">
                            <button 
                                class="btn btn--secondary btn--full" 
                                on:click={handleDetectAILines} 
                                disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                                title="Analyze each line individually"
                            >
                                📝 Line-by-Line Analysis
                            </button>
                            <div class="button-description">
                                Analyzes each line separately to identify which specific lines are AI-generated.
                            </div>

                            <button 
                                class="btn btn--secondary btn--full" 
                                on:click={handleDetectAISentences} 
                                disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                                title="Analyze each sentence individually"
                            >
                                🔤 Sentence-by-Sentence Analysis
                            </button>
                            <div class="button-description">
                                Breaks down text into sentences and analyzes each one for AI patterns.
                            </div>

                            <button 
                                class="btn btn--secondary btn--full" 
                                on:click={handleHighlightAIText} 
                                disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                                title="Highlight AI-generated portions in the text"
                            >
                                🖍️ Highlight AI Content
                            </button>
                            <div class="button-description">
                                Visually marks AI-generated portions in {$detectionFormat} format.
                            </div>

                            <button 
                                class="btn btn--tertiary btn--full" 
                                on:click={handleGetAILines} 
                                disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                                title="Get simple list of AI lines"
                            >
                                📋 List AI Lines Only
                            </button>
                            <div class="button-description">
                                Simple backup method to get just the AI-generated lines as a list.
                            </div>
                        </div>
                    </div>

                    <!-- Humanization Actions -->
                    <div class="action-group">
                        <h4 class="action-title">
                            🤖➡️👤 Text Humanization
                            <small class="action-description">Transform AI text to appear human-written</small>
                        </h4>
                        <div class="action-buttons">
                            <button 
                                class="btn btn--combined btn--full" 
                                on:click={handleHumanizeAndCheck} 
                                disabled={$isProcessing || $isDetecting || !$inputText.trim()}
                                title="Humanize text and verify the improvement"
                            >
                                {#if $isProcessing && $currentStep === 'humanizing and checking'}
                                    <div class="spinner"></div>
                                    Processing & Checking...
                                {:else}
                                    ✨ Humanize & Verify
                                {/if}
                            </button>
                            <div class="button-description">
                                Humanizes text and immediately checks if AI detection improved.
                            </div>

                            <button 
                                class="btn btn--primary btn--full" 
                                on:click={handleHumanizeWithSingleModel} 
                                disabled={$isProcessing || !$inputText.trim()}
                                title="Standard humanization with selected model"
                            >
                                {#if $isProcessing && $processingMode === 'single'}
                                    <div class="spinner"></div>
                                    {$currentStep === 'paraphrasing' ? 'Paraphrasing...' : 
                                     $currentStep === 'rewriting' ? 'Rewriting...' : 'Processing...'}
                                {:else}
                                    🎯 Standard Humanization
                                {/if}
                            </button>
                            <div class="button-description">
                                Two-step process: Paraphrasing + Rewriting with {$selectedModel || 'current model'}.
                                {$useEnhanced ? 'Enhanced mode enabled.' : 'Standard mode.'}
                            </div>
                        </div>
                    </div>

                    <!-- Pipeline Processing -->
                    <div class="action-group">
                        <h4 class="action-title">
                            🔄 Pipeline Processing
                            <small class="action-description">Multi-model sequential processing for maximum effectiveness</small>
                        </h4>
                        <div class="action-buttons">
                            <button 
                                class="btn btn--secondary btn--full" 
                                on:click={handleParaphraseWithMultiModels} 
                                disabled={$isProcessing || !$inputText.trim()}
                                title="Process with 2 best models sequentially"
                            >
                                {#if $isProcessing && $processingMode === 'multi'}
                                    <div class="spinner"></div>
                                    Pipeline processing...
                                {:else}
                                    🥈 2-Model Pipeline
                                {/if}
                            </button>
                            <div class="button-description">
                                Uses 2 best-performing models in sequence. Each model processes the previous model's output.
                            </div>

                            <button 
                                class="btn btn--secondary btn--full" 
                                on:click={handleParaphraseWithAllModels} 
                                disabled={$isProcessing || !$inputText.trim()}
                                title="Process with all available models sequentially"
                            >
                                {#if $isProcessing && $processingMode === 'all'}
                                    <div class="spinner"></div>
                                    Full pipeline processing...
                                {:else}
                                    🥇 Full {$availableModels.length}-Model Pipeline
                                {/if}
                            </button>
                            <div class="button-description">
                                Maximum processing power. All {$availableModels.length} models process sequentially for ultimate humanization.
                                Slowest but most thorough.
                            </div>
                        </div>
                    </div>
                </section>
            </aside>

            <!-- Right Content Area (70%) -->
            <div class="content">
                <!-- Input Section -->
                <section class="input-section">
                    <div class="input-header">
                        <label class="input-label">Enter AI-generated text to humanize</label>
                        <div class="stats">
                            {$characterCount} / 50,000 chars • {$wordCount} words
                        </div>
                    </div>
                    
                    <textarea
                        bind:value={$inputText}
                        placeholder="Paste your AI-generated text here..."
                        class="textarea"
                        rows="15"
                        maxlength="50000"
                    ></textarea>
                </section>

                <!-- Error Display -->
                {#if $error}
                    <div class="error">
                        <span class="error__icon">⚠</span>
                        {$error}
                    </div>
                {/if}

                <!-- Line Detection Results -->
                {#if $lineDetectionResults}
                    <section class="results">
                        <h2 class="results__title">Line Detection Results</h2>
                        <div class="detection-summary">
                            <div class="detection-stats">
                                <span class="stat">AI Lines: {$lineDetectionResults.statistics.ai_generated_lines}</span>
                                <span class="stat">Total Lines: {$lineDetectionResults.statistics.total_lines_analyzed}</span>
                                <span class="stat">AI Percentage: {($lineDetectionResults.statistics.ai_percentage * 100).toFixed(1)}%</span>
                            </div>
                        </div>
                        
                        <div class="line-results">
                            {#each $lineDetectionResults.line_results as line, index}
                                <div class="line-item" class:ai-line={line.is_ai_generated}>
                                    <div class="line-header">
                                        <span class="line-number">Line {index + 1}</span>
                                        <span class="line-prediction" class:ai-detected={line.is_ai_generated}>
                                            {line.is_ai_generated ? 'AI' : 'Human'} ({(line.ai_probability * 100).toFixed(1)}%)
                                        </span>
                                    </div>
                                    <div class="line-text">{line.text}</div>
                                </div>
                            {/each}
                        </div>
                    </section>
                {/if}

                <!-- Sentence Detection Results -->
                {#if $sentenceDetectionResults}
                    <section class="results">
                        <h2 class="results__title">Sentence Detection Results</h2>
                        <div class="detection-summary">
                            <div class="detection-stats">
                                <span class="stat">AI Sentences: {$sentenceDetectionResults.statistics.ai_generated_sentences}</span>
                                <span class="stat">Total Sentences: {$sentenceDetectionResults.statistics.total_sentences_analyzed}</span>
                                <span class="stat">AI Percentage: {($sentenceDetectionResults.statistics.ai_percentage * 100).toFixed(1)}%</span>
                            </div>
                        </div>
                        
                        <div class="sentence-results">
                            {#each $sentenceDetectionResults.sentence_results as sentence, index}
                                <div class="sentence-item" class:ai-sentence={sentence.is_ai_generated}>
                                    <div class="sentence-header">
                                        <span class="sentence-number">#{index + 1}</span>
                                        <span class="sentence-prediction" class:ai-detected={sentence.is_ai_generated}>
                                            {sentence.is_ai_generated ? 'AI' : 'Human'} ({(sentence.ai_probability * 100).toFixed(1)}%)
                                        </span>
                                    </div>
                                    <div class="sentence-text">{sentence.text}</div>
                                </div>
                            {/each}
                        </div>
                    </section>
                {/if}

                <!-- Fixed Highlighted Text Results -->
                {#if $highlightedText}
                    <section class="results">
                        <h2 class="results__title">Highlighted AI Text</h2>
                        <div class="detection-summary">
                            <div class="detection-stats">
                                <span class="stat">Format: {$detectionFormat}</span>
                                <span class="stat">Threshold: {$detectionThreshold}</span>
                            </div>
                        </div>
                        <div class="highlighted-content">
                            {#if $detectionFormat === 'html'}
                                <!-- Safely render HTML with proper styling -->
                                <div class="highlighted-html">
                                    {@html $highlightedText}
                                </div>
                            {:else if $detectionFormat === 'markdown'}
                                <!-- Fixed markdown parsing -->
                                <div class="highlighted-markdown">
                                    {#each $highlightedText.split(/(\*\*[^*]+\*\*)/) as part, i}
                                        {#if part.match(/^\*\*.*\*\*$/)}
                                            <mark class="ai-highlight">{part.slice(2, -2)}</mark>
                                        {:else if part.trim()}
                                            <span>{part}</span>
                                        {/if}
                                    {/each}
                                </div>
                            {:else}
                                <!-- Fixed plain text with bracket highlighting -->
                                <div class="highlighted-plain">
                                    {#each $highlightedText.split(/(\[[^\]]+\])/) as part, i}
                                        {#if part.match(/^\[.*\]$/)}
                                            <mark class="ai-highlight">{part.slice(1, -1)}</mark>
                                        {:else if part.trim()}
                                            <span>{part}</span>
                                        {/if}
                                    {/each}
                                </div>
                            {/if}
                        </div>
                        <div class="highlight-actions">
                            <button class="copy-btn" on:click={() => copyToClipboard($highlightedText)}>
                                Copy Highlighted Text
                            </button>
                        </div>
                    </section>
                {/if}

                <!-- New AI Lines Backup Display -->
                {#if $showAILines && $aiLinesSimple && $aiLinesSimple.length > 0}
                    <section class="results">
                        <h2 class="results__title">AI-Generated Lines (Simple List)</h2>
                        <div class="detection-summary">
                            <div class="detection-stats">
                                <span class="stat">Found: {$aiLinesSimple.length} AI lines</span>
                                <span class="stat">Threshold: {$detectionThreshold}</span>
                            </div>
                        </div>
                        
                        <div class="ai-lines-simple">
                            <div class="ai-lines-header">
                                <h4>Lines identified as AI-generated:</h4>
                                <button class="copy-btn" on:click={() => copyToClipboard($aiLinesSimple.join('\n'))}>
                                    Copy All AI Lines
                                </button>
                            </div>
                            <div class="ai-lines-list">
                                {#each $aiLinesSimple as line, index}
                                    <div class="ai-line-item">
                                        <div class="ai-line-number">#{index + 1}</div>
                                        <div class="ai-line-text">{line}</div>
                                        <button class="copy-btn copy-btn--small" on:click={() => copyToClipboard(line)}>
                                            Copy
                                        </button>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    </section>
                {/if}

                <!-- AI Detection Results -->
                {#if $showDetectionResults && $detectionResults}
                    <section class="results">
                        <h2 class="results__title">AI Detection Results</h2>
                        
                        <div class="detection-summary">
                            <div class="detection-main">
                                <div class="prediction-badge" class:ai-detected={$detectionResults.is_ai_generated} class:human-detected={!$detectionResults.is_ai_generated}>
                                    {$detectionResults.prediction || ($detectionResults.is_ai_generated ? 'AI-Generated' : 'Human-Written')}
                                </div>
                                <div class="confidence-meter">
                                    <div class="confidence-label">Confidence: {($detectionResults.confidence || $detectionResults.ai_probability || 0).toFixed(3)}</div>
                                    <div class="confidence-bar">
                                        <div 
                                            class="confidence-fill" 
                                            class:ai-confidence={$detectionResults.is_ai_generated}
                                            style="width: {(($detectionResults.confidence || $detectionResults.ai_probability || 0) * 100)}%"
                                        ></div>
                                    </div>
                                </div>
                            </div>

                            <div class="detection-stats">
                                {#if $detectionResults.ai_probability !== undefined}
                                    <span class="stat">AI: {($detectionResults.ai_probability * 100).toFixed(1)}%</span>
                                {/if}
                                {#if $detectionResults.human_probability !== undefined}
                                    <span class="stat">Human: {($detectionResults.human_probability * 100).toFixed(1)}%</span>
                                {/if}
                                <span class="stat">Mode: {$detectionResults.mode}</span>
                                <span class="stat">Length: {$detectionResults.text_length || $inputText.length} chars</span>
                            </div>
                        </div>

                        <!-- Detailed Results based on mode -->
                        {#if $detectionResults.mode === 'ensemble' && $detectionResults.individual_results}
                            <div class="ensemble-details">
                                <h4>Individual Model Results</h4>
                                <div class="model-results">
                                    {#each $detectionResults.individual_results as result}
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

                        {#if $detectionResults.mode === 'segments' && $detectionResults.segment_results}
                            <div class="segment-details">
                                <h4>Segment Analysis</h4>
                                <div class="segment-stats">
                                    <span class="badge">Total: {$detectionResults.total_segments}</span>
                                    <span class="badge">Consistency: {($detectionResults.consistency * 100).toFixed(1)}%</span>
                                    <span class="badge">Segment Length: {$detectionResults.segment_length_used}</span>
                                </div>
                                <div class="segment-results">
                                    {#each $detectionResults.segment_results as segment, index}
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
                {#if $showCombinedResults && $combinedResults}
                    <section class="results">
                        <h2 class="results__title">Humanization & Detection Results</h2>
                        
                        <div class="combined-summary">
                            <div class="improvement-badge" class:improved={$combinedResults.improvement.detection_improved} class:not-improved={!$combinedResults.improvement.detection_improved}>
                                {$combinedResults.improvement.detection_improved ? 'Detection Improved! ✓' : 'No Improvement ✗'}
                            </div>
                            
                            <div class="improvement-stats">
                                <span>
                                    Reduction: {($combinedResults.improvement.ai_probability_reduction * 100).toFixed(1)}%
                                </span>
                                <span>
                                    Improvement: {$combinedResults.improvement.percentage_improvement.toFixed(1)}%
                                </span>
                            </div>
                        </div>

                        <div class="before-after">
                            <div class="detection-comparison">
                                <div class="before-detection">
                                    <h4>Before Humanization</h4>
                                    <div class="detection-result">
                                        <div class="prediction-small" class:ai-detected={$combinedResults.original_detection.is_ai_generated}>
                                            {$combinedResults.original_detection.prediction}
                                        </div>
                                        <div class="probability">AI: {($combinedResults.original_detection.ai_probability * 100).toFixed(1)}%</div>
                                    </div>
                                </div>

                                <div class="after-detection">
                                    <h4>After Humanization</h4>
                                    <div class="detection-result">
                                        <div class="prediction-small" class:ai-detected={$combinedResults.humanized_detection.is_ai_generated} class:human-detected={!$combinedResults.humanized_detection.is_ai_generated}>
                                            {$combinedResults.humanized_detection.prediction}
                                        </div>
                                        <div class="probability">AI: {($combinedResults.humanized_detection.ai_probability * 100).toFixed(1)}%</div>
                                    </div>
                                </div>
                            </div>

                            <div class="text-comparison">
                                <div class="text-before">
                                    <div class="text-header">
                                        <h4>Original Text</h4>
                                        <button class="copy-btn" on:click={() => copyToClipboard($combinedResults.original_text)}>
                                            Copy
                                        </button>
                                    </div>
                                    <div class="text-content">
                                        {$combinedResults.original_text}
                                    </div>
                                </div>

                                <div class="text-after">
                                    <div class="text-header">
                                        <h4>Humanized Text</h4>
                                        <button class="copy-btn copy-btn--primary" on:click={() => copyToClipboard($combinedResults.humanized_text)}>
                                            Copy
                                        </button>
                                    </div>
                                    <div class="text-content">
                                        {$combinedResults.humanized_text}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                {/if}

                <!-- Pipeline Results -->
                {#if $showMultiResults && ($multiResults || $allResults)}
                    <section class="results">
                        <h2 class="results__title">
                            {$multiResults ? '2-Model Pipeline Results' : 'Full Pipeline Results'}
                        </h2>
                        <p class="results__subtitle">
                            Pipeline mode: Each model processes the output of the previous model. 
                            Choose any step's output to continue with rewriting:
                        </p>
                        
                        {#if $multiResults}
                            <div class="pipeline-summary">
                                <span class="badge badge--success">{$multiResults.statistics.successful_steps} successful</span>
                                <span class="badge badge--error">{$multiResults.statistics.failed_steps} failed</span>
                                <span class="badge">Length change: {$multiResults.statistics.total_length_change}</span>
                                <span class="badge">Mode: {$multiResults.statistics.pipeline_mode}</span>
                            </div>

                            <div class="pipeline-flow">
                                <div class="pipeline-step pipeline-step--original">
                                    <div class="pipeline-step__header">
                                        <strong>Original Text</strong>
                                        <div class="pipeline-step__actions">
                                            <button class="copy-btn" on:click={() => copyToClipboard($multiResults.original_text)}>
                                                Copy
                                            </button>
                                            <button 
                                                class="btn btn--primary btn--small" 
                                                on:click={() => handleContinueToRewrite($multiResults.original_text, 'original')}
                                                disabled={$isProcessing}
                                            >
                                                Skip to Rewrite
                                            </button>
                                        </div>
                                    </div>
                                    <div class="pipeline-step__text">
                                        {$multiResults.original_text}
                                    </div>
                                    <div class="pipeline-step__meta">
                                        {$multiResults.statistics.original_length} chars
                                    </div>
                                </div>

                                {#each $multiResults.pipeline_results as result, index}
                                    <div class="pipeline-arrow">↓ Model {result.step}: {result.model}</div>
                                    
                                    <div class="pipeline-step" class:pipeline-step--failed={!result.success} class:pipeline-step--final={index === $multiResults.pipeline_results.length - 1}>
                                        <div class="pipeline-step__header">
                                            <strong>
                                                <span class="status-dot" class:success={result.success} class:failed={!result.success}></span>
                                                Step {result.step} Output
                                                {#if index === $multiResults.pipeline_results.length - 1}
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
                                                        on:click={() => handleContinueToRewrite(result.output_text, result.model)}
                                                        disabled={$isProcessing}
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

                        {#if $allResults}
                            <div class="pipeline-summary">
                                <span class="badge badge--success">{$allResults.statistics.successful_steps} successful</span>
                                <span class="badge badge--error">{$allResults.statistics.failed_steps} failed</span>
                                <span class="badge">{$allResults.statistics.total_processing_time}s total</span>
                                <span class="badge">Length change: {$allResults.statistics.total_length_change}</span>
                                <span class="badge">Mode: {$allResults.statistics.pipeline_mode}</span>
                            </div>

                            <div class="pipeline-flow">
                                <div class="pipeline-step pipeline-step--original">
                                    <div class="pipeline-step__header">
                                        <strong>Original Text</strong>
                                        <div class="pipeline-step__actions">
                                            <button class="copy-btn" on:click={() => copyToClipboard($allResults.original_text)}>
                                                Copy
                                            </button>
                                            <button 
                                                class="btn btn--primary btn--small" 
                                                on:click={() => handleContinueToRewrite($allResults.original_text, 'original')}
                                                disabled={$isProcessing}
                                            >
                                                Skip to Rewrite
                                            </button>
                                        </div>
                                    </div>
                                    <div class="pipeline-step__text">
                                        {$allResults.original_text}
                                    </div>
                                    <div class="pipeline-step__meta">
                                        {$allResults.statistics.original_length} chars
                                    </div>
                                </div>

                                {#each $allResults.pipeline_results as result, index}
                                    <div class="pipeline-arrow">
                                        ↓ Model {result.step}: {result.model}
                                        {#if result.processing_time}
                                            <small>({result.processing_time}s)</small>
                                        {/if}
                                    </div>
                                    
                                    <div class="pipeline-step" class:pipeline-step--failed={!result.success} class:pipeline-step--final={index === $allResults.pipeline_results.length - 1}>
                                        <div class="pipeline-step__header">
                                            <strong>
                                                <span class="status-dot" class:success={result.success} class:failed={!result.success}></span>
                                                Step {result.step} Output
                                                {#if index === $allResults.pipeline_results.length - 1}
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
                                                        on:click={() => handleContinueToRewrite(result.output_text, result.model)}
                                                        disabled={$isProcessing}
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
                {#if $results.final && !$showMultiResults}
                    <section class="results">
                        <h2 class="results__title">Humanized Text</h2>
                        
                        <!-- Show both steps -->
                        <div class="pipeline-results">
                            {#if $results.paraphrased}
                                <div class="step-result">
                                    <div class="step-result__header">
                                        <h3>Step 1: Paraphrased</h3>
                                        <button class="copy-btn" on:click={() => copyToClipboard($results.paraphrased)}>
                                            Copy
                                        </button>
                                    </div>
                                    <div class="step-result__text">
                                        {$results.paraphrased}
                                    </div>
                                </div>
                            {/if}

                            <div class="step-result step-result--final">
                                <div class="step-result__header">
                                    <h3>Step 2: Final Humanized Text</h3>
                                    <button class="copy-btn copy-btn--primary" on:click={() => copyToClipboard($results.final)}>
                                        Copy Final
                                    </button>
                                </div>
                                <div class="step-result__text">
                                    {$results.final}
                                </div>
                                
                                {#if $statistics && Object.keys($statistics).length > 0}
                                    <div class="quick-stats">
                                        <span>
                                            {$statistics.original_length || 0} → {$statistics.paraphrased_length || 0} → {$statistics.final_length || $statistics.rewritten_length || 0} chars
                                        </span>
                                        {#if $statistics.model_used}
                                            <span>• Model: {$statistics.model_used}</span>
                                        {/if}
                                        {#if $statistics.enhanced_rewriting_used}
                                            <span>• Enhanced rewriting</span>
                                        {/if}
                                    </div>
                                {/if}
                            </div>
                        </div>
                    </section>
                {/if}
            </div>
        </div>
    </main>
</div>

<style>
    /* Enhanced styles for better UX */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .help-btn {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 1px solid var(--border-color);
        background: var(--bg-secondary);
        color: var(--text-secondary);
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .help-btn:hover {
        background: var(--primary-color);
        color: white;
    }

    .help-panel {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        font-size: 13px;
    }

    .help-list {
        margin: 0.5rem 0 0 0;
        padding-left: 1rem;
    }

    .help-list li {
        margin-bottom: 0.5rem;
    }

    .config-description {
        display: block;
        color: var(--text-secondary);
        font-size: 11px;
        margin-top: 2px;
        line-height: 1.3;
    }

    .option__description {
        display: block;
        margin-top: 4px;
        color: var(--text-secondary);
        font-size: 11px;
        line-height: 1.3;
    }

    .model-info {
        background: var(--bg-tertiary);
        border-radius: 6px;
        padding: 0.75rem;
        margin-top: 0.5rem;
        font-size: 12px;
    }

    .model-info__row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.25rem;
    }

    .model-info__label {
        font-weight: 500;
        color: var(--text-secondary);
    }

    .model-info__value {
        color: var(--text-primary);
    }

    .model-description {
        margin-top: 0.5rem;
        font-style: italic;
        color: var(--text-secondary);
    }

    .model-selection {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        background: var(--bg-tertiary);
    }

    .quick-select {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }

    .model-checkboxes {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 0.5rem;
        background: var(--bg-primary);
    }

    .model-checkbox {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        padding: 0.75rem;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .model-checkbox:hover {
        background: var(--bg-secondary);
    }

    .model-checkbox__content {
        flex: 1;
    }

    .model-checkbox__name {
        font-weight: 500;
        font-size: 13px;
        margin-bottom: 0.25rem;
    }

    .model-checkbox__meta {
        display: flex;
        gap: 0.5rem;
        font-size: 11px;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
    }

    .model-checkbox__description {
        font-size: 11px;
        color: var(--text-secondary);
        font-style: italic;
    }

    .selection-summary {
        margin-top: 0.5rem;
        font-size: 12px;
        color: var(--text-secondary);
        text-align: center;
    }

    .threshold-container {
        margin-top: 0.5rem;
    }

    .threshold-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 0.25rem;
        font-size: 10px;
        color: var(--text-secondary);
    }

    .advanced-config {
        background: var(--bg-tertiary);
        border-radius: 8px;
        padding: 1rem;
        margin-top: 0.5rem;
        border-left: 3px solid var(--primary-color);
    }

    .action-title {
        margin: 0 0 0.25rem 0;
        font-size: 14px;
        font-weight: 600;
    }

    .action-description {
        display: block;
        font-size: 11px;
        color: var(--text-secondary);
        font-weight: normal;
        margin-top: 2px;
    }

    .button-description {
        font-size: 11px;
        color: var(--text-secondary);
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
        line-height: 1.3;
        padding: 0 0.5rem;
    }

    .btn--text {
        background: transparent;
        border: none;
        color: var(--primary-color);
        text-decoration: none;
        padding: 0.25rem 0;
    }

    .btn--text:hover {
        text-decoration: underline;
    }

    /* Fixed highlighting styles */
    .highlighted-content {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: var(--space-md);
        background: var(--bg-secondary);
        font-family: inherit;
        line-height: 1.5;
        font-size: 0.8125rem;
    }

    .highlighted-html,
    .highlighted-markdown,
    .highlighted-plain {
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    /* Improved AI highlighting */
    .ai-highlight {
        background: linear-gradient(135deg, #fef3c7, #fbbf24);
        color: #92400e;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: 600;
        border: 1px solid #f59e0b;
        box-shadow: 0 1px 2px rgba(251, 191, 36, 0.2);
    }

    /* Fix for HTML highlighting */
    .highlighted-html mark,
    .highlighted-html [style*="background"] {
        background: linear-gradient(135deg, #fef3c7, #fbbf24) !important;
        color: #92400e !important;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: 600;
        border: 1px solid #f59e0b;
    }

    /* New AI Lines Simple Display */
    .ai-lines-simple {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        background: var(--bg-primary);
    }

    .ai-lines-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--space-md);
        border-bottom: 1px solid var(--border-light);
        background: var(--bg-secondary);
    }

    .ai-lines-header h4 {
        margin: 0;
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .ai-lines-list {
        max-height: 400px;
        overflow-y: auto;
    }

    .ai-line-item {
        display: flex;
        align-items: flex-start;
        gap: var(--space-sm);
        padding: var(--space-md);
        border-bottom: 1px solid var(--border-light);
        transition: background-color 0.2s;
    }

    .ai-line-item:hover {
        background: var(--bg-secondary);
    }

    .ai-line-item:last-child {
        border-bottom: none;
    }

    .ai-line-number {
        flex-shrink: 0;
        width: 30px;
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 500;
        text-align: center;
        background: var(--bg-tertiary);
        border-radius: var(--radius-sm);
        padding: var(--space-xs);
    }

    .ai-line-text {
        flex: 1;
        font-size: 0.8125rem;
        line-height: 1.4;
        color: var(--text-primary);
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    .copy-btn--small {
        padding: var(--space-xs);
        font-size: 0.625rem;
        min-width: auto;
    }

    /* Tertiary button style */
    .btn--tertiary {
        background: var(--bg-tertiary);
        color: var(--text-secondary);
        border: 1px solid var(--border);
    }

    .btn--tertiary:hover {
        background: var(--bg-secondary);
        color: var(--text-primary);
        border-color: var(--primary);
    }

    .btn--tertiary:disabled {
        background: var(--bg-tertiary);
        color: var(--text-muted);
        border-color: var(--border-light);
        cursor: not-allowed;
    }

    /* Responsive adjustments */
    @media (max-width: 1200px) {
        .main-container {
            flex-direction: column;
        }
        
        .sidebar {
            width: 100%;
            margin-bottom: 2rem;
        }
        
        .content {
            width: 100%;
        }
    }

    @media (max-width: 768px) {
        .ai-lines-header {
            flex-direction: column;
            gap: var(--space-sm);
            align-items: stretch;
        }
        
        .ai-line-item {
            flex-direction: column;
            gap: var(--space-xs);
        }
        
        .ai-line-number {
            width: auto;
            text-align: left;
        }
    }
</style>
