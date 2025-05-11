/**
 * Proletto File Sharing JavaScript
 * Handles the UI interactions for the file sharing page
 */

// Variables for storing state
let currentProject = {
    id: null,
    name: '',
    workspace_id: null
};

let currentFiles = [];
let customFolders = [];
let currentFolder = 'all';
let currentView = 'grid';
let currentUser = {
    id: null,
    name: '',
    email: ''
};

// On page load
document.addEventListener('DOMContentLoaded', () => {
    // Extract IDs from URL
    const ids = getIdsFromUrl();
    
    if (!ids.projectId || !ids.workspaceId) {
        // No IDs in URL, redirect to workspaces list
        window.location.href = '/workspace';
        return;
    }
    
    // Store project info
    currentProject.id = ids.projectId;
    currentProject.workspace_id = ids.workspaceId;
    
    // Set up event listeners
    setupEventListeners();
    
    // Fetch user profile
    fetchUserProfile();
    
    // Fetch project details
    fetchProjectDetails(ids.projectId);
    
    // Fetch files
    fetchFiles(ids.projectId);
});

// Fetch user profile information
function fetchUserProfile() {
    fetch('/api/user/profile')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch user profile');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                currentUser.id = data.user.id;
                currentUser.name = data.user.name || data.user.email;
                currentUser.email = data.user.email;
                
                // Update UI with user information
                document.getElementById('user-name').textContent = currentUser.name;
            }
        })
        .catch(error => {
            console.error('Error fetching user profile:', error);
        });
}

// Fetch project details
function fetchProjectDetails(projectId) {
    fetch(`/api/projects/${projectId}`)
        .then(response => {
            if (!response.ok) {
                if (response.status === 403) {
                    // User doesn't have access to this project
                    window.location.href = `/workspace/${currentProject.workspace_id}`;
                    return null;
                }
                throw new Error('Failed to fetch project details');
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Redirect handled in the response check
            
            if (data.success) {
                // Store project data
                currentProject.name = data.project.name;
                
                // Update page title
                document.title = `${data.project.name} - Files - Proletto`;
                
                // Update page heading
                document.querySelector('.files-title h1').textContent = `${data.project.name} - Files`;
                
                // Update back button
                const backBtn = document.getElementById('back-to-project-btn');
                backBtn.addEventListener('click', () => {
                    window.location.href = `/workspace/${currentProject.workspace_id}/project/${currentProject.id}`;
                });
            } else {
                showError(data.error || 'Failed to load project');
            }
        })
        .catch(error => {
            console.error('Error fetching project details:', error);
            showError('Failed to load project. Please try again later.');
        });
}

// Fetch files for the project
function fetchFiles(projectId) {
    fetch(`/api/projects/${projectId}/files`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch files');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Store files data
                currentFiles = data.files || [];
                customFolders = data.folders || [];
                
                // Add custom folders to UI
                updateFolderList();
                
                // Render files
                renderFiles();
            } else {
                showError(data.error || 'Failed to load files');
            }
        })
        .catch(error => {
            console.error('Error fetching files:', error);
            showError('Failed to load files. Please try again later.');
        });
}

// Update folder list with custom folders
function updateFolderList() {
    const folderList = document.querySelector('.folder-list');
    const defaultFolderCount = 4; // All Files, Images, Documents, Other
    
    // Remove existing custom folders
    while (folderList.children.length > defaultFolderCount) {
        folderList.removeChild(folderList.lastChild);
    }
    
    // Add custom folders
    customFolders.forEach(folder => {
        const folderItem = document.createElement('li');
        folderItem.className = 'folder-item';
        folderItem.dataset.folder = folder.id;
        
        folderItem.innerHTML = `
            <div class="folder-icon">📁</div>
            <div class="folder-name">${escapeHtml(folder.name)}</div>
            <div class="file-count" id="folder-${folder.id}-count">0</div>
        `;
        
        folderList.appendChild(folderItem);
    });
    
    // Add click events to all folder items
    document.querySelectorAll('.folder-item').forEach(item => {
        item.addEventListener('click', () => {
            switchFolder(item.dataset.folder);
        });
    });
    
    // Add custom folders to upload selector
    const uploadFolderSelect = document.getElementById('upload-folder');
    
    // Clear custom folder options
    while (uploadFolderSelect.options.length > 4) {
        uploadFolderSelect.remove(4);
    }
    
    // Add custom folder options
    customFolders.forEach(folder => {
        const option = document.createElement('option');
        option.value = folder.id;
        option.textContent = folder.name;
        uploadFolderSelect.appendChild(option);
    });
}

// Render files in the UI
function renderFiles() {
    const gridView = document.getElementById('files-grid-view');
    const listView = document.getElementById('files-list-body');
    const emptyState = document.getElementById('empty-files-state');
    
    // Clear views
    while (gridView.firstChild) {
        if (gridView.firstChild.id === 'empty-files-state') {
            break;
        }
        gridView.removeChild(gridView.firstChild);
    }
    
    listView.innerHTML = '';
    
    // Filter files by current folder
    let filteredFiles = currentFiles;
    
    if (currentFolder === 'all') {
        // No additional filtering needed for 'all'
    } else if (currentFolder === 'images') {
        filteredFiles = currentFiles.filter(file => 
            file.file_type && ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml'].includes(file.file_type.toLowerCase())
        );
    } else if (currentFolder === 'documents') {
        filteredFiles = currentFiles.filter(file => 
            file.file_type && ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'].includes(file.file_type.toLowerCase())
        );
    } else if (currentFolder === 'other') {
        filteredFiles = currentFiles.filter(file => {
            if (!file.file_type) return true;
            
            const type = file.file_type.toLowerCase();
            return !['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 
                     'application/pdf', 'application/msword', 
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                     'text/plain'].includes(type);
        });
    } else {
        // Custom folder
        filteredFiles = currentFiles.filter(file => file.folder_id === currentFolder);
    }
    
    // Update file counts
    updateFileCounts();
    
    // Check if there are any files
    if (filteredFiles.length === 0) {
        emptyState.style.display = 'block';
        return;
    }
    
    // Hide empty state
    emptyState.style.display = 'none';
    
    // Sort files by upload date (newest first)
    filteredFiles.sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at));
    
    // Render files in grid view
    filteredFiles.forEach(file => {
        // Grid view
        const card = createFileCard(file);
        gridView.appendChild(card);
        
        // List view
        const row = createFileRow(file);
        listView.appendChild(row);
    });
}

// Create a file card for grid view
function createFileCard(file) {
    const card = document.createElement('div');
    card.className = 'file-card';
    card.dataset.id = file.id;
    
    // Determine file icon/preview based on file type
    let previewHtml = '';
    
    if (file.file_type && file.file_type.startsWith('image/')) {
        previewHtml = `<img src="${file.file_path}" alt="${escapeHtml(file.filename)}">`;
    } else {
        // Display appropriate icon based on file type
        let iconText = '📄';
        
        if (file.file_type) {
            const type = file.file_type.toLowerCase();
            if (type.includes('pdf')) {
                iconText = '📑';
            } else if (type.includes('word') || type.includes('document')) {
                iconText = '📝';
            } else if (type.includes('spreadsheet') || type.includes('excel')) {
                iconText = '📊';
            } else if (type.includes('presentation') || type.includes('powerpoint')) {
                iconText = '📽️';
            } else if (type.includes('audio')) {
                iconText = '🎵';
            } else if (type.includes('video')) {
                iconText = '🎬';
            } else if (type.includes('zip') || type.includes('archive')) {
                iconText = '📦';
            }
        }
        
        previewHtml = `<div class="file-icon">${iconText}</div>`;
    }
    
    // Format file size
    const fileSize = formatFileSize(file.file_size);
    
    // Format upload date
    const uploadDate = new Date(file.uploaded_at).toLocaleDateString();
    
    card.innerHTML = `
        <div class="file-preview">
            ${previewHtml}
        </div>
        <div class="file-info">
            <div class="file-name">${escapeHtml(file.filename)}</div>
            <div class="file-meta">
                <span>${fileSize}</span>
                <span>${uploadDate}</span>
            </div>
        </div>
    `;
    
    // Add click event to open file preview
    card.addEventListener('click', () => {
        openFilePreview(file);
    });
    
    return card;
}

// Create a file row for list view
function createFileRow(file) {
    const row = document.createElement('tr');
    row.dataset.id = file.id;
    
    // Determine file icon based on file type
    let iconText = '📄';
    
    if (file.file_type) {
        const type = file.file_type.toLowerCase();
        if (type.startsWith('image/')) {
            iconText = '🖼️';
        } else if (type.includes('pdf')) {
            iconText = '📑';
        } else if (type.includes('word') || type.includes('document')) {
            iconText = '📝';
        } else if (type.includes('spreadsheet') || type.includes('excel')) {
            iconText = '📊';
        } else if (type.includes('presentation') || type.includes('powerpoint')) {
            iconText = '📽️';
        } else if (type.includes('audio')) {
            iconText = '🎵';
        } else if (type.includes('video')) {
            iconText = '🎬';
        } else if (type.includes('zip') || type.includes('archive')) {
            iconText = '📦';
        }
    }
    
    // Format file size
    const fileSize = formatFileSize(file.file_size);
    
    // Format upload date
    const uploadDate = new Date(file.uploaded_at).toLocaleDateString();
    
    // Get uploader info
    const uploaderName = file.uploader ? file.uploader.name : 'Unknown';
    
    row.innerHTML = `
        <td>
            <div class="file-list-name">
                <span>${iconText}</span>
                <span>${escapeHtml(file.filename)}</span>
            </div>
        </td>
        <td>${fileSize}</td>
        <td>${escapeHtml(uploaderName)}</td>
        <td>${uploadDate}</td>
        <td>
            <div class="file-actions">
                <button class="file-action-btn preview-btn" title="Preview">👁️</button>
                <button class="file-action-btn download-btn" title="Download">⬇️</button>
                <button class="file-action-btn delete-btn" title="Delete">🗑️</button>
            </div>
        </td>
    `;
    
    // Add event listeners for actions
    const previewBtn = row.querySelector('.preview-btn');
    const downloadBtn = row.querySelector('.download-btn');
    const deleteBtn = row.querySelector('.delete-btn');
    
    previewBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        openFilePreview(file);
    });
    
    downloadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        downloadFile(file);
    });
    
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        confirmDeleteFile(file);
    });
    
    // Add click event to row to open file preview
    row.addEventListener('click', () => {
        openFilePreview(file);
    });
    
    return row;
}

// Update file counts for folders
function updateFileCounts() {
    // Count files in each category
    const counts = {
        all: currentFiles.length,
        images: 0,
        documents: 0,
        other: 0
    };
    
    // Count custom folder files
    customFolders.forEach(folder => {
        counts[folder.id] = 0;
    });
    
    // Count files by type
    currentFiles.forEach(file => {
        // Count by folder
        if (file.folder_id && counts[file.folder_id] !== undefined) {
            counts[file.folder_id]++;
        }
        
        // Count by file type
        if (file.file_type) {
            const type = file.file_type.toLowerCase();
            if (type.startsWith('image/')) {
                counts.images++;
            } else if (['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'].includes(type)) {
                counts.documents++;
            } else {
                counts.other++;
            }
        } else {
            counts.other++;
        }
    });
    
    // Update UI with counts
    document.getElementById('all-files-count').textContent = counts.all;
    document.getElementById('images-count').textContent = counts.images;
    document.getElementById('documents-count').textContent = counts.documents;
    document.getElementById('other-count').textContent = counts.other;
    
    // Update custom folder counts
    customFolders.forEach(folder => {
        const countElement = document.getElementById(`folder-${folder.id}-count`);
        if (countElement) {
            countElement.textContent = counts[folder.id] || 0;
        }
    });
}

// Switch to a different folder
function switchFolder(folderId) {
    // Update current folder
    currentFolder = folderId;
    
    // Update active folder in UI
    const folderItems = document.querySelectorAll('.folder-item');
    folderItems.forEach(item => {
        if (item.dataset.folder === folderId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Re-render files
    renderFiles();
}

// Switch between grid and list view
function switchView(viewType) {
    // Update current view
    currentView = viewType;
    
    // Update active view in UI
    const viewButtons = document.querySelectorAll('.view-toggle-btn');
    viewButtons.forEach(btn => {
        if (btn.dataset.view === viewType) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Show/hide views
    const gridView = document.getElementById('files-grid-view');
    const listView = document.getElementById('files-list-view');
    
    if (viewType === 'grid') {
        gridView.style.display = 'grid';
        listView.style.display = 'none';
    } else {
        gridView.style.display = 'none';
        listView.style.display = 'block';
    }
}

// Open file preview modal
function openFilePreview(file) {
    const modal = document.getElementById('preview-modal');
    const container = document.getElementById('preview-container');
    
    // Set file name
    document.getElementById('preview-file-name').textContent = file.filename;
    
    // Create preview content based on file type
    let previewContent = '';
    
    if (file.file_type && file.file_type.startsWith('image/')) {
        previewContent = `<img src="${file.file_path}" alt="${escapeHtml(file.filename)}" class="preview-image">`;
    } else if (file.file_type && file.file_type === 'application/pdf') {
        previewContent = `<iframe src="${file.file_path}" class="preview-document"></iframe>`;
    } else {
        // Files that can't be previewed
        previewContent = `
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 4rem; margin-bottom: 20px;">📄</div>
                <p>Preview not available for this file type</p>
                <p>Download the file to view its contents</p>
            </div>
        `;
    }
    
    container.innerHTML = previewContent;
    
    // Set file info
    document.getElementById('preview-file-type').textContent = file.file_type || 'Unknown';
    document.getElementById('preview-file-size').textContent = formatFileSize(file.file_size);
    document.getElementById('preview-uploader').textContent = file.uploader ? file.uploader.name : 'Unknown';
    document.getElementById('preview-upload-date').textContent = new Date(file.uploaded_at).toLocaleDateString();
    document.getElementById('preview-description').value = file.description || '';
    
    // Set up download button
    const downloadBtn = document.getElementById('preview-download-btn');
    downloadBtn.onclick = () => downloadFile(file);
    
    // Set up delete button
    const deleteBtn = document.getElementById('preview-delete-btn');
    deleteBtn.onclick = () => {
        modal.style.display = 'none';
        confirmDeleteFile(file);
    };
    
    // Show the modal
    modal.style.display = 'flex';
}

// Download a file
function downloadFile(file) {
    // Create a temporary link and click it to start download
    const link = document.createElement('a');
    link.href = file.file_path;
    link.download = file.filename;
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Confirm file deletion
function confirmDeleteFile(file) {
    if (confirm(`Are you sure you want to delete "${file.filename}"? This action cannot be undone.`)) {
        deleteFile(file.id);
    }
}

// Delete a file
function deleteFile(fileId) {
    fetch(`/api/files/${fileId}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to delete file');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Remove file from local array
            const index = currentFiles.findIndex(f => f.id === fileId);
            if (index !== -1) {
                currentFiles.splice(index, 1);
            }
            
            // Re-render files
            renderFiles();
            
            // Show success message
            showSuccess('File deleted successfully');
        } else {
            showError(data.error || 'Failed to delete file');
        }
    })
    .catch(error => {
        console.error('Error deleting file:', error);
        showError('Failed to delete file. Please try again later.');
    });
}

// Handle file upload
function handleFileUpload(files, folderId, description) {
    // Create FormData object
    const formData = new FormData();
    
    // Add each file
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    // Add folder ID
    formData.append('folder_id', folderId);
    
    // Add description if provided
    if (description) {
        formData.append('description', description);
    }
    
    // Add project ID
    formData.append('project_id', currentProject.id);
    
    // Upload files
    fetch('/api/files/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to upload files');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Add new files to local array
            if (data.files && data.files.length > 0) {
                currentFiles = [...currentFiles, ...data.files];
            }
            
            // Re-render files
            renderFiles();
            
            // Show success message
            showSuccess('Files uploaded successfully');
            
            // Close the upload modal
            document.getElementById('upload-modal').style.display = 'none';
            
            // Reset the file input
            document.getElementById('file-input').value = '';
            document.getElementById('upload-file-list').innerHTML = '';
        } else {
            showError(data.error || 'Failed to upload files');
        }
    })
    .catch(error => {
        console.error('Error uploading files:', error);
        showError('Failed to upload files. Please try again later.');
    });
}

// Create a new folder
function createFolder(folderName) {
    fetch('/api/folders', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: folderName,
            project_id: currentProject.id
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to create folder');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Add new folder to local array
            customFolders.push(data.folder);
            
            // Update folder list
            updateFolderList();
            
            // Switch to the new folder
            switchFolder(data.folder.id);
            
            // Show success message
            showSuccess('Folder created successfully');
            
            // Close the folder modal
            document.getElementById('folder-modal').style.display = 'none';
            
            // Reset the form
            document.getElementById('folder-form').reset();
        } else {
            showError(data.error || 'Failed to create folder');
        }
    })
    .catch(error => {
        console.error('Error creating folder:', error);
        showError('Failed to create folder. Please try again later.');
    });
}

// Handle selected files for upload
function handleSelectedFiles(files) {
    const fileList = document.getElementById('upload-file-list');
    fileList.innerHTML = '';
    
    // Display selected files
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Check file size
        if (file.size > 20 * 1024 * 1024) { // 20MB
            showError(`File "${file.name}" exceeds the 20MB size limit and will not be uploaded.`);
            continue;
        }
        
        const fileItem = document.createElement('div');
        fileItem.className = 'upload-file-item';
        
        const fileSize = formatFileSize(file.size);
        
        fileItem.innerHTML = `
            <div class="upload-file-icon">📄</div>
            <div class="upload-file-name">${escapeHtml(file.name)}</div>
            <div class="upload-file-size">${fileSize}</div>
            <button type="button" class="upload-file-remove" data-index="${i}">&times;</button>
        `;
        
        fileList.appendChild(fileItem);
    }
    
    // Handle file removal
    document.querySelectorAll('.upload-file-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.upload-file-item').remove();
        });
    });
}

// Set up event listeners
function setupEventListeners() {
    // View toggling
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchView(btn.dataset.view);
        });
    });
    
    // Search functionality
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', () => {
        const searchTerm = searchInput.value.toLowerCase();
        if (searchTerm === '') {
            renderFiles(); // Reset to normal view
            return;
        }
        
        // Filter files by search term
        const filteredFiles = currentFiles.filter(file => 
            file.filename.toLowerCase().includes(searchTerm) ||
            (file.description && file.description.toLowerCase().includes(searchTerm))
        );
        
        // Update UI with filtered files
        renderFilteredFiles(filteredFiles);
    });
    
    // Upload button
    document.getElementById('upload-file-btn').addEventListener('click', () => {
        document.getElementById('upload-file-list').innerHTML = '';
        document.getElementById('upload-modal').style.display = 'flex';
    });
    
    // Empty state upload button
    document.getElementById('empty-upload-btn').addEventListener('click', () => {
        document.getElementById('upload-file-list').innerHTML = '';
        document.getElementById('upload-modal').style.display = 'flex';
    });
    
    // Create folder button
    document.getElementById('create-folder-btn').addEventListener('click', () => {
        document.getElementById('folder-form').reset();
        document.getElementById('folder-modal').style.display = 'flex';
    });
    
    // File input and drop area
    const fileInput = document.getElementById('file-input');
    const dropArea = document.getElementById('drop-area');
    
    fileInput.addEventListener('change', () => {
        handleSelectedFiles(fileInput.files);
    });
    
    dropArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Drag and drop handling
    dropArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropArea.style.borderColor = '#8d6e63';
    });
    
    dropArea.addEventListener('dragleave', () => {
        dropArea.style.borderColor = '#e0e0e0';
    });
    
    dropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dropArea.style.borderColor = '#e0e0e0';
        handleSelectedFiles(e.dataTransfer.files);
    });
    
    // Upload form submission
    document.getElementById('upload-form').addEventListener('submit', (e) => {
        e.preventDefault();
        
        const files = fileInput.files;
        const folder = document.getElementById('upload-folder').value;
        const description = document.getElementById('upload-description').value.trim();
        
        if (files.length === 0) {
            showError('Please select at least one file to upload');
            return;
        }
        
        handleFileUpload(files, folder, description);
    });
    
    // Folder form submission
    document.getElementById('folder-form').addEventListener('submit', (e) => {
        e.preventDefault();
        
        const folderName = document.getElementById('folder-name').value.trim();
        
        if (!folderName) {
            showError('Please enter a folder name');
            return;
        }
        
        createFolder(folderName);
    });
    
    // Modal close buttons
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
        });
    });
    
    // Cancel buttons
    document.getElementById('cancel-upload').addEventListener('click', () => {
        document.getElementById('upload-modal').style.display = 'none';
    });
    
    document.getElementById('cancel-folder').addEventListener('click', () => {
        document.getElementById('folder-modal').style.display = 'none';
    });
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        document.querySelectorAll('.modal').forEach(modal => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// Render filtered files
function renderFilteredFiles(filteredFiles) {
    const gridView = document.getElementById('files-grid-view');
    const listView = document.getElementById('files-list-body');
    const emptyState = document.getElementById('empty-files-state');
    
    // Clear views
    while (gridView.firstChild) {
        if (gridView.firstChild.id === 'empty-files-state') {
            break;
        }
        gridView.removeChild(gridView.firstChild);
    }
    
    listView.innerHTML = '';
    
    // Check if there are any files
    if (filteredFiles.length === 0) {
        emptyState.style.display = 'block';
        emptyState.querySelector('h3').textContent = 'No matching files';
        emptyState.querySelector('p').textContent = 'Try a different search term or folder.';
        emptyState.querySelector('#empty-upload-btn').style.display = 'none';
        return;
    }
    
    // Hide empty state
    emptyState.style.display = 'none';
    
    // Sort files by upload date (newest first)
    filteredFiles.sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at));
    
    // Render files in grid view
    filteredFiles.forEach(file => {
        // Grid view
        const card = createFileCard(file);
        gridView.appendChild(card);
        
        // List view
        const row = createFileRow(file);
        listView.appendChild(row);
    });
}

// Helper function to get IDs from URL
function getIdsFromUrl() {
    const path = window.location.pathname;
    const match = path.match(/\/workspace\/(\d+)\/project\/(\d+)\/files/);
    
    if (match) {
        return {
            workspaceId: match[1],
            projectId: match[2]
        };
    }
    
    return { workspaceId: null, projectId: null };
}

// Helper function to format file size
function formatFileSize(bytes) {
    if (!bytes) return 'Unknown';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
}

// Helper function to show error messages
function showError(message) {
    // In a real app, you might use a toast or notification system
    alert(message);
}

// Helper function to show success messages
function showSuccess(message) {
    // In a real app, you might use a toast or notification system
    alert(message);
}

// Helper function to safely escape HTML
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}