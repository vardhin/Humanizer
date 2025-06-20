<script>
    import { onMount } from 'svelte';
    import { derived } from 'svelte/store';
    import '$lib/style.css';
    
    // Import Lucide icons
    import { 
        Search, Target, BarChart3, CheckSquare, Star, FileText,
        Zap, Users, Bot, ArrowRight, Copy, RefreshCw, Eye,
        Settings, HelpCircle, Lightbulb, Play, ChevronDown,
        ChevronRight, AlertTriangle, CheckCircle, XCircle,
        ArrowDown, Hash, FileEdit, Highlighter,
        Sparkles, GitBranch, Layers, TestTube, Activity,
        TrendingUp, Clock, Gauge, Shield, Info, AlertCircle,
        FileOutput
    } from 'lucide-svelte';
    
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
        lineDetectionResults, highlightedText,
        detectionFormat, useAllDetectionModels, topNModels, detectionCriteria,
        minLineLength,
        
        // Functions
        copyToClipboard, loadBackendInfo, humanizeWithSingleModel,
        loadDetectionModels, detectAIText, humanizeAndCheck,
        
        // Enhanced detection functions
        detectAILines, highlightAIText,
        detectWithAllModels, detectWithSelectedModels, detectWithTopModels,
        getDetectionModelInfo, getRecommendedDetectionModel,
        
        // Add the missing function
        validateDetectionInput, showToast,
        
        // Import the new humanization model info function
        getHumanizationModelInfo, getRecommendedHumanizationModel
    } from '$lib/script.js';

    // New stores for enhanced configuration
    import { writable } from 'svelte/store';
    const selectedDetectionModels = writable([]);
    const showAdvancedConfig = writable(false);
    const showDetectionHelp = writable(false);
    const showHumanizationHelp = writable(false);

    // Remove the selectedHumanizationModels store since we don't need it for radio buttons
    // const selectedHumanizationModels = writable([]);

    // Derived stores for computed values
    const characterCount = derived(inputText, $inputText => $inputText.length);
    const wordCount = derived(inputText, $inputText => 
        $inputText.trim().split(/\s+/).filter(word => word.length > 0).length
    );

    // Get detection model info
    const detectionModelInfo = getDetectionModelInfo();
    // Get humanization model info
    const humanizationModelInfo = getHumanizationModelInfo();

    // Handler functions that pass the reactive values to the imported functions
    const handleHumanizeWithSingleModel = () => {
        humanizeWithSingleModel($inputText, $selectedModel, $useEnhanced);
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

    // Simplify the recommendation functions
    const setRecommendedHumanizationModels = (criteria) => {
        const recommended = getRecommendedHumanizationModel(criteria);
        selectedModel.set(recommended);
    };

    onMount(() => {
        try {
            loadBackendInfo();
            loadDetectionModels();
            // Set default selected detection model
            selectedDetectionModels.set([getRecommendedDetectionModel('performance')]);
            // Set default selected humanization model - much simpler!
            selectedModel.set(getRecommendedHumanizationModel('performance'));
        } catch (err) {
            console.error('Failed to initialize:', err);
        }
    });
</script>

<svelte:head>
    <title>VHumanize</title>
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
    <!-- Action Navigation Bar with Brand -->
    <nav class="nav-bar">
        <div class="nav-container">
            <div class="nav-brand">
                <h1 class="brand-title">VHumanize</h1>
                {#if $backendStatus}
                    <div class="status-dot" class:status-dot--connected={$backendStatus.status === 'healthy'}></div>
                {/if}
            </div>

            <div class="nav-sections">
                <!-- AI Detection Actions -->
                <div class="nav-section">
                    <div class="nav-section__title">AI Detection</div>
                    <div class="nav-buttons">
                        <button 
                            class="nav-btn nav-btn--detection" 
                            on:click={handleDetectAIText} 
                            disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                            title="Detect AI content using configured settings"
                        >
                            {#if $isDetecting}
                                <div class="spinner"></div>
                                Detecting...
                            {:else}
                                <Target size={16} />
                                Smart Detection
                            {/if}
                        </button>
                        
                        <button 
                            class="nav-btn nav-btn--detection" 
                            on:click={handleDetectWithAllModels} 
                            disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                            title="Run detection with all available models"
                        >
                            <BarChart3 size={16} />
                            All Models
                        </button>
                    </div>
                </div>

                <!-- Advanced Analysis -->
                <div class="nav-section">
                    <div class="nav-section__title">Advanced Analysis</div>
                    <div class="nav-buttons">
                        <button 
                            class="nav-btn nav-btn--advanced" 
                            on:click={handleDetectAILines} 
                            disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                            title="Analyze each line individually"
                        >
                            <FileText size={16} />
                            Line Analysis
                        </button>
                        
                        <button 
                            class="nav-btn nav-btn--advanced" 
                            on:click={handleHighlightAIText} 
                            disabled={$isDetecting || $isProcessing || !$inputText.trim()}
                            title="Highlight AI-generated portions"
                        >
                            <Highlighter size={16} />
                            Highlight AI
                        </button>
                    </div>
                </div>

                <!-- Text Humanization -->
                <div class="nav-section">
                    <div class="nav-section__title">Humanization</div>
                    <div class="nav-buttons">
                        <button 
                            class="nav-btn nav-btn--combined" 
                            on:click={handleHumanizeAndCheck} 
                            disabled={$isProcessing || $isDetecting || !$inputText.trim()}
                            title="Humanize text and verify improvement"
                        >
                            {#if $isProcessing && $currentStep === 'humanizing and checking'}
                                <div class="spinner"></div>
                                Processing...
                            {:else}
                                <Sparkles size={16} />
                                Humanize & Verify
                            {/if}
                        </button>
                        
                        <button 
                            class="nav-btn nav-btn--humanize" 
                            on:click={handleHumanizeWithSingleModel} 
                            disabled={$isProcessing || !$inputText.trim()}
                            title="Standard humanization"
                        >
                            {#if $isProcessing && $processingMode === 'single'}
                                <div class="spinner"></div>
                                {$currentStep === 'paraphrasing' ? 'Paraphrasing...' : 
                                 $currentStep === 'rewriting' ? 'Rewriting...' : 'Processing...'}
                            {:else}
                                <Target size={16} />
                                Standard
                            {/if}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <main class="main">
        <div class="main-container">
            <!-- Configuration Sidebar (Only Config Options) -->
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
                                <HelpCircle size={12} />
                            </button>
                        </h3>
                    </div>

                    {#if $showHumanizationHelp}
                        <div class="help-panel">
                            <h4><Lightbulb size={16} class="inline-icon" />How Humanization Works:</h4>
                            <ul class="help-list">
                                <li><strong>Step 1:</strong> Paraphrasing - Restructures sentences while keeping meaning</li>
                                <li><strong>Step 2:</strong> Rewriting - Applies human-like patterns and styles</li>
                                <li><strong>Enhanced:</strong> Uses advanced prompts for better quality (slower)</li>
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
                                    Choose a specific model for humanization. Different models have varying writing styles and capabilities.
                                </small>
                            </label>
                            
                            <div class="model-selection">
                                <div class="quick-select">
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedHumanizationModels('performance')}
                                    >
                                        Best Performance
                                    </button>
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedHumanizationModels('speed')}
                                    >
                                        Fastest
                                    </button>
                                    <button 
                                        class="btn btn--small btn--secondary" 
                                        on:click={() => setRecommendedHumanizationModels('balanced')}
                                    >
                                        Balanced
                                    </button>
                                </div>

                                <div class="model-checkboxes">
                                    {#each $availableModels as model}
                                        <label class="model-checkbox">
                                            <input 
                                                type="radio" 
                                                name="humanization-model"
                                                value={model}
                                                bind:group={$selectedModel}
                                            />
                                            <div class="model-checkbox__content">
                                                <div class="model-checkbox__name">
                                                    {humanizationModelInfo[model]?.name || model}
                                                </div>
                                                <div class="model-checkbox__meta">
                                                    <span class="model-type">{humanizationModelInfo[model]?.type}</span>
                                                    <span class="model-speed">Speed: {humanizationModelInfo[model]?.speed}</span>
                                                    <span class="model-accuracy">Acc: {humanizationModelInfo[model]?.accuracy}</span>
                                                </div>
                                                <div class="model-checkbox__description">
                                                    {humanizationModelInfo[model]?.description}
                                                </div>
                                            </div>
                                        </label>
                                    {/each}
                                </div>
                                
                                <div class="selection-summary">
                                    Selected: {humanizationModelInfo[$selectedModel]?.name || $selectedModel || 'None'}
                                </div>
                            </div>
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
                                <HelpCircle size={12} />
                            </button>
                        </h3>
                    </div>

                    {#if $showDetectionHelp}
                        <div class="help-panel">
                            <h4><TestTube size={16} class="inline-icon" />Detection Modes Explained:</h4>
                            <ul class="help-list">
                                <li><strong>Ensemble:</strong> Combines multiple models for better accuracy</li>
                                <li><strong>Single Model:</strong> Uses one specific detection model</li>
                                <li><strong>All Models:</strong> Runs all available models and shows individual results</li>
                                <li><strong>Top N Models:</strong> Uses the best performing models based on criteria</li>
                                <li><strong>Line Analysis:</strong> Analyzes text line by line</li>
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
                            <option value="selected">☑️ Selected Models Only</option>
                            <option value="top_models">⭐ Top N Models</option>
                            <option value="segments">📄 Segment Analysis</option>
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
                                <option value="performance">📈 Best Overall Performance</option>
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
                            {#if $showAdvancedConfig}
                                <ChevronDown size={14} />
                            {:else}
                                <ChevronRight size={14} />
                            {/if}
                            Advanced Options
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
                                    <option value="markdown">📄 Markdown (** bold **)</option>
                                    <option value="html">👁️ HTML (&lt;mark&gt; tags)</option>
                                    <option value="plain">📤 Plain Text (brackets)</option>
                                </select>
                            </div>
                        </div>
                    {/if}
                </section>
            </aside>

            <!-- Right Content Area -->
            <div class="content">
                <!-- Input Section -->
                <section class="input-section">
                    <div class="input-header">
                        <label class="input-label">
                            <FileEdit size={18} class="inline-icon" />
                            Enter AI-generated text to humanize
                        </label>
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
                        <AlertTriangle size={16} class="error__icon" />
                        {$error}
                    </div>
                {/if}

                <!-- Line Detection Results -->
                {#if $lineDetectionResults && $lineDetectionResults.line_results}
                    <section class="results">
                        <h2 class="results__title">Line Detection Results</h2>
                        <div class="detection-summary">
                            <div class="detection-stats">
                                <span class="stat">AI Lines: {$lineDetectionResults.statistics.ai_generated_lines}</span>
                                <span class="stat">Total Lines: {$lineDetectionResults.statistics.total_lines_analyzed}</span>
                                <span class="stat">AI Percentage: {$lineDetectionResults.statistics.ai_percentage.toFixed(1)}%</span>
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
                                <Copy size={14} />
                                Copy Highlighted Text
                            </button>
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
                                    <div class="confidence-label">
                                        <Gauge size={14} />
                                        Confidence: {($detectionResults.confidence || $detectionResults.ai_probability || 0).toFixed(3)}
                                    </div>
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
                                                <span class="segment-number"><Hash size={14} />#{index + 1}</span>
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
                                {#if $combinedResults.improvement.detection_improved}
                                    <CheckCircle size={16} />
                                    Detection Improved!
                                {:else}
                                    <XCircle size={16} />
                                    No Improvement
                                {/if}
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
                                            <Copy size={14} />
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
                                            <Copy size={14} />
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
                                            <Copy size={14} />
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
                                        <Copy size={14} />
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
    .inline-icon {
        display: inline-block;
        vertical-align: middle;
        margin-right: 0.25rem;
    }
    
    /* Enhanced model selection styles */
    .model-badge {
        display: inline-block;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        margin-left: 8px;
    }
    
    .model-badge--t5 {
        background: #e3f2fd;
        color: #1565c0;
    }
    
    .model-badge--transformer {
        background: #f3e5f5;
        color: #7b1fa2;
    }
    
    .model-ratings {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin: 8px 0;
    }
    
    .model-rating {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
    }
    
    .rating-label {
        font-weight: 500;
        color: var(--text-secondary);
    }
    
    .rating-stars {
        font-family: monospace;
        color: #ffc107;
        font-size: 11px;
        letter-spacing: 1px;
    }
    
    .model-type-badge {
        background: var(--surface-2);
        color: var(--text-secondary);
        padding: 2px 6px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: 500;
        text-transform: capitalize;
    }
    
    .model-status {
        font-size: 11px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 10px;
    }
    
    .model-status--loaded {
        background: #e8f5e8;
        color: #2e7d32;
    }
    
    .model-status--available {
        background: #fff3e0;
        color: #ef6c00;
    }
    
    .model-recommendation {
        margin-top: 6px;
        font-size: 11px;
        font-weight: 600;
        color: var(--accent);
        text-align: center;
        padding: 4px;
        background: var(--accent-bg);
        border-radius: 4px;
    }
    
    .selection-summary {
        margin-top: 16px;
        padding: 12px;
        background: var(--surface-1);
        border-radius: 8px;
        border: 1px solid var(--border);
    }
    
    .selected-model {
        margin-bottom: 8px;
        font-size: 14px;
    }
    
    .selected-model-details {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 12px;
        color: var(--text-secondary);
    }
    
    .detail-item {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    .quick-select {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 8px;
        margin-bottom: 16px;
    }
    
    .quick-select .btn {
        font-size: 12px;
        padding: 6px 8px;
        white-space: nowrap;
    }
</style>

