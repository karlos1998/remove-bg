document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadSection = document.getElementById('upload-section');
    const processSection = document.getElementById('process-section');
    const errorToast = document.getElementById('error-toast');
    const errorMsg = document.getElementById('error-msg');
    
    const fileListContainer = document.getElementById('file-list');
    const processAllBtn = document.getElementById('process-all-btn');
    const resetAllBtn = document.getElementById('reset-all-btn');

    // Cropper elements
    const cropModal = document.getElementById('crop-modal');
    const cropImage = document.getElementById('crop-image');
    const saveCropBtn = document.getElementById('save-crop');
    const cancelCropBtn = document.getElementById('cancel-crop');
    const closeCropModalBtn = document.getElementById('close-crop-modal');

    let filesQueue = []; 
    let cropper = null;
    let currentCroppingId = null;

    // Event Listeners
    if (dropZone) {
        dropZone.addEventListener('click', () => fileInput.click());

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('drop-zone--over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('drop-zone--over');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            handleFiles(e.dataTransfer.files);
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
    }

    if (resetAllBtn) resetAllBtn.addEventListener('click', resetAll);
    if (processAllBtn) processAllBtn.addEventListener('click', processAll);
    if (cancelCropBtn) cancelCropBtn.addEventListener('click', closeCrop);
    if (closeCropModalBtn) closeCropModalBtn.addEventListener('click', closeCrop);
    if (saveCropBtn) saveCropBtn.addEventListener('click', saveCrop);

    // Core Functions
    function handleFiles(files) {
        if (files.length === 0) return;
        
        const newFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
        if (newFiles.length === 0) {
            showError('Please select image files.');
            return;
        }

        newFiles.forEach(file => {
            const id = Math.random().toString(36).substr(2, 9);
            const originalUrl = URL.createObjectURL(file);
            filesQueue.push({
                id,
                file,
                originalUrl,
                resultUrl: null,
                status: 'ready',
                progress: 0,
                error: null
            });
        });
        
        renderFileList();
        uploadSection.classList.add('hidden');
        processSection.classList.remove('hidden');
        errorToast.classList.add('hidden');
    }

    function renderFileList() {
        if (!fileListContainer) return;
        fileListContainer.innerHTML = '';
        
        filesQueue.forEach(item => {
            const card = document.createElement('div');
            card.className = `glass-card rounded-2xl overflow-hidden flex flex-col transition-all duration-300 ${item.status === 'processing' ? 'ring-2 ring-indigo-500 scale-[1.02]' : 'hover:shadow-lg'}`;
            
            const isDone = item.status === 'done';
            const isProcessing = item.status === 'processing';
            
            card.innerHTML = `
                <div class="relative aspect-square bg-slate-50 group">
                    <img src="${isDone ? item.resultUrl : item.originalUrl}" 
                         class="w-full h-full object-contain ${isDone ? 'checkerboard' : ''}" 
                         id="img-${item.id}">
                    
                    ${isProcessing ? `
                        <div class="absolute inset-0 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center p-6">
                            <div class="spinner mb-4"></div>
                            <span class="text-xs font-bold text-indigo-600 tracking-wider uppercase">Removing background...</span>
                        </div>
                    ` : ''}

                    ${item.status === 'ready' ? `
                        <div class="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center justify-center gap-3">
                            <button onclick="window.ui.openCrop('${item.id}')" class="bg-white text-slate-800 w-10 h-10 rounded-full flex items-center justify-center hover:bg-indigo-500 hover:text-white transition-all shadow-xl" title="Crop">
                                <i class="fas fa-crop-alt"></i>
                            </button>
                            <button onclick="window.ui.rotateFile('${item.id}')" class="bg-white text-slate-800 w-10 h-10 rounded-full flex items-center justify-center hover:bg-indigo-500 hover:text-white transition-all shadow-xl" title="Rotate">
                                <i class="fas fa-redo"></i>
                            </button>
                            <button onclick="window.ui.removeFile('${item.id}')" class="bg-white text-red-500 w-10 h-10 rounded-full flex items-center justify-center hover:bg-red-500 hover:text-white transition-all shadow-xl" title="Remove">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                    ` : ''}
                </div>
                
                <div class="p-4 flex flex-col flex-1">
                    <div class="flex items-center justify-between mb-3">
                        <span class="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest truncate max-w-[150px]">${item.file.name}</span>
                        ${isDone ? '<span class="flex items-center text-emerald-600 text-[10px] font-black tracking-tighter"><i class="fas fa-check-circle mr-1"></i> DONE</span>' : ''}
                        ${item.status === 'error' ? '<span class="flex items-center text-red-500 text-[10px] font-black tracking-tighter"><i class="fas fa-exclamation-circle mr-1"></i> ERROR</span>' : ''}
                    </div>
                    
                    <div class="mt-auto space-y-2">
                        ${isDone ? `
                            <div class="flex gap-2">
                                <button onclick="window.ui.rotateResult('${item.id}')" class="flex-1 bg-slate-100 text-slate-700 py-2 rounded-xl font-bold text-xs hover:bg-slate-200 transition-all">
                                    <i class="fas fa-redo mr-1"></i> Rotate
                                </button>
                                <a href="${item.resultUrl}" download="no-bg-${item.file.name.split('.')[0]}.png" class="flex-[2] text-center bg-indigo-600 text-white py-2 rounded-xl font-bold text-xs hover:bg-indigo-700 transition-all shadow-md">
                                    <i class="fas fa-download mr-1"></i> Download
                                </a>
                            </div>
                        ` : `
                            <button onclick="window.ui.processSingle('${item.id}')" ${isProcessing ? 'disabled' : ''} class="w-full bg-slate-900 text-white py-2.5 rounded-xl font-bold text-xs hover:bg-slate-800 transition-all disabled:opacity-50">
                                ${isProcessing ? 'Processing...' : 'Remove background'}
                            </button>
                        `}
                    </div>
                </div>
            `;
            fileListContainer.appendChild(card);
        });

        if (processAllBtn) {
            processAllBtn.disabled = !filesQueue.some(f => f.status === 'ready');
        }
    }

    async function processSingle(id) {
        const item = filesQueue.find(f => f.id === id);
        if (!item || item.status !== 'ready') return;

        item.status = 'processing';
        renderFileList();

        const formData = new FormData();
        formData.append('file', item.file);

        try {
            const response = await fetch('/api/remove', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Server error');

            const blob = await response.blob();
            item.resultUrl = URL.createObjectURL(blob);
            item.status = 'done';
        } catch (err) {
            item.status = 'error';
            item.error = err.message;
            showError(`Error processing ${item.file.name}: ${err.message}`);
        }
        renderFileList();
    }

    async function processAll() {
        const readyItems = filesQueue.filter(f => f.status === 'ready');
        const concurrency = 2;
        
        for (let i = 0; i < readyItems.length; i += concurrency) {
            const batch = readyItems.slice(i, i + concurrency);
            await Promise.all(batch.map(item => processSingle(item.id)));
        }
    }

    function removeFile(id) {
        const index = filesQueue.findIndex(f => f.id === id);
        if (index > -1) {
            URL.revokeObjectURL(filesQueue[index].originalUrl);
            if (filesQueue[index].resultUrl) URL.revokeObjectURL(filesQueue[index].resultUrl);
            filesQueue.splice(index, 1);
            
            if (filesQueue.length === 0) {
                resetAll();
            } else {
                renderFileList();
            }
        }
    }

    function resetAll() {
        filesQueue.forEach(f => {
            URL.revokeObjectURL(f.originalUrl);
            if (f.resultUrl) URL.revokeObjectURL(f.resultUrl);
        });
        filesQueue = [];
        if (uploadSection) uploadSection.classList.remove('hidden');
        if (processSection) processSection.classList.add('hidden');
        if (fileInput) fileInput.value = '';
        if (errorToast) errorToast.classList.add('hidden');
    }

    async function rotateFile(id, isResult = false) {
        const item = filesQueue.find(f => f.id === id);
        if (!item) return;
        
        const urlToRotate = isResult ? item.resultUrl : item.originalUrl;
        if (!urlToRotate) return;

        const img = new Image();
        img.src = urlToRotate;
        
        await new Promise(resolve => img.onload = resolve);

        const canvas = document.createElement('canvas');
        canvas.width = img.height;
        canvas.height = img.width;
        
        const ctx = canvas.getContext('2d');
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(90 * Math.PI / 180); // Rotate 90 degrees right
        ctx.drawImage(img, -img.width / 2, -img.height / 2);

        canvas.toBlob((blob) => {
            const url = URL.createObjectURL(blob);
            if (isResult) {
                URL.revokeObjectURL(item.resultUrl);
                item.resultUrl = url;
            } else {
                URL.revokeObjectURL(item.originalUrl);
                item.originalUrl = url;
                const fileName = item.file.name.split('.')[0] + '-rotated.png';
                item.file = new File([blob], fileName, { type: 'image/png' });
            }
            renderFileList();
        }, 'image/png');
    }

    function openCrop(id) {
        const item = filesQueue.find(f => f.id === id);
        if (!item) return;

        currentCroppingId = id;
        cropImage.src = item.originalUrl;
        cropModal.classList.remove('hidden');
        
        if (cropper) cropper.destroy();
        
        cropper = new Cropper(cropImage, {
            viewMode: 2,
            autoCropArea: 1,
            responsive: true
        });
    }

    function closeCrop() {
        cropModal.classList.add('hidden');
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }
        currentCroppingId = null;
    }

    function saveCrop() {
        if (!cropper || !currentCroppingId) return;
        
        const item = filesQueue.find(f => f.id === currentCroppingId);
        const canvas = cropper.getCroppedCanvas({ maxWidth: 4096, maxHeight: 4096 });
        
        canvas.toBlob((blob) => {
            const url = URL.createObjectURL(blob);
            URL.revokeObjectURL(item.originalUrl);
            item.originalUrl = url;
            
            const fileName = item.file.name.split('.')[0] + '-cropped.png';
            item.file = new File([blob], fileName, { type: 'image/png' });
            
            renderFileList();
            closeCrop();
        }, 'image/png');
    }

    function showError(msg) {
        if (errorMsg) errorMsg.textContent = msg;
        if (errorToast) errorToast.classList.remove('hidden');
    }

    // Expose functions to window for onclick handlers
    window.ui = {
        removeFile,
        processSingle,
        rotateFile,
        rotateResult: (id) => rotateFile(id, true),
        openCrop
    };
});
