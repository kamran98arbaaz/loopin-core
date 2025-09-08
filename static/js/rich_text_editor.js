// Rich Text Editor Integration using Quill.js
class RichTextEditor {
    constructor() {
        this.editors = new Map();
        this.init();
    }

    init() {
        // Initialize editors for all rich text areas
        this.initUpdateEditor();
        this.initSOPEditor();
        this.initLessonEditor();
    }

    initUpdateEditor() {
        const container = document.getElementById('message-editor');
        if (container) {
            const quill = new Quill(container, {
                theme: 'snow',
                placeholder: 'Describe your update in detail. Include progress, challenges, insights, and next steps...',
                modules: {
                    toolbar: [
                        ['bold', 'italic', 'underline'],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['link'],
                        ['clean']
                    ]
                }
            });

            // Create hidden input to store HTML content
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'message';
            hiddenInput.id = 'message-hidden';
            container.parentNode.appendChild(hiddenInput);

            // Update hidden input when content changes
            quill.on('text-change', () => {
                hiddenInput.value = quill.root.innerHTML;
            });

            this.editors.set('message', quill);
        }
    }

    initSOPEditor() {
        const container = document.getElementById('summary_text-editor');
        if (container) {
            const quill = new Quill(container, {
                theme: 'snow',
                placeholder: 'Provide a comprehensive summary of the standard operating procedure...',
                modules: {
                    toolbar: [
                        ['bold', 'italic', 'underline'],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['link'],
                        ['clean']
                    ]
                }
            });

            // Create hidden input to store HTML content
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'summary_text';
            hiddenInput.id = 'summary_text-hidden';
            container.parentNode.appendChild(hiddenInput);

            // Update hidden input when content changes
            quill.on('text-change', () => {
                hiddenInput.value = quill.root.innerHTML;
            });

            this.editors.set('summary_text', quill);
        }
    }

    initLessonEditor() {
        // Initialize content editor
        const contentContainer = document.getElementById('content-editor');
        if (contentContainer) {
            const contentQuill = new Quill(contentContainer, {
                theme: 'snow',
                placeholder: 'Describe the lesson learned in detail. Include context, what happened, what was learned, and how it can be applied...',
                modules: {
                    toolbar: [
                        ['bold', 'italic', 'underline'],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['link'],
                        ['clean']
                    ]
                }
            });

            // Create hidden input for content
            const contentHidden = document.createElement('input');
            contentHidden.type = 'hidden';
            contentHidden.name = 'content';
            contentHidden.id = 'content-hidden';
            contentContainer.parentNode.appendChild(contentHidden);

            contentQuill.on('text-change', () => {
                contentHidden.value = contentQuill.root.innerHTML;
            });

            this.editors.set('content', contentQuill);
        }

        // Initialize summary editor
        const summaryContainer = document.getElementById('summary-editor');
        if (summaryContainer) {
            const summaryQuill = new Quill(summaryContainer, {
                theme: 'snow',
                placeholder: 'Optional: Provide a brief summary of the key takeaway...',
                modules: {
                    toolbar: [
                        ['bold', 'italic', 'underline'],
                        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                        ['link'],
                        ['clean']
                    ]
                }
            });

            // Create hidden input for summary
            const summaryHidden = document.createElement('input');
            summaryHidden.type = 'hidden';
            summaryHidden.name = 'summary';
            summaryHidden.id = 'summary-hidden';
            summaryContainer.parentNode.appendChild(summaryHidden);

            summaryQuill.on('text-change', () => {
                summaryHidden.value = summaryQuill.root.innerHTML;
            });

            this.editors.set('summary', summaryQuill);
        }
    }

    // Method to set content for editing
    setContent(editorName, content) {
        const editor = this.editors.get(editorName);
        if (editor && content) {
            editor.root.innerHTML = content;
        }
    }

    // Method to get content
    getContent(editorName) {
        const editor = this.editors.get(editorName);
        return editor ? editor.root.innerHTML : '';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.richTextEditor = new RichTextEditor();
});