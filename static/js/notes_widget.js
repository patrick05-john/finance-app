document.addEventListener('DOMContentLoaded', function() {
    const addNoteBtn = document.getElementById('addNoteBtn');
    const noteForm = document.getElementById('noteForm');
    const cancelNoteBtn = document.getElementById('cancelNoteBtn');
    const saveNoteBtn = document.getElementById('saveNoteBtn');
    const emptyNotesState = document.getElementById('emptyNotesState');
    const savedNotesList = document.getElementById('savedNotesList');
    const noteTitle = document.getElementById('noteTitle');
    const noteContent = document.getElementById('noteContent');

    // Keep track of note count to toggle the empty state watermark
    let notesCount = 0;

    addNoteBtn.addEventListener('click', () => {
        noteForm.style.display = 'block';
        emptyNotesState.style.display = 'none';
        addNoteBtn.style.display = 'none';
    });

    cancelNoteBtn.addEventListener('click', () => {
        noteForm.style.display = 'none';
        addNoteBtn.style.display = 'block';
        if (notesCount === 0) {
            emptyNotesState.style.display = 'block';
        }
    });

    saveNoteBtn.addEventListener('click', () => {
        const titleVal = noteTitle.value.trim();
        const contentVal = noteContent.value.trim();
        
        if (titleVal === '' && contentVal === '') return;

        // Create new note UI element
        const noteDiv = document.createElement('div');
        noteDiv.className = 'p-3 border rounded bg-light note-item shadow-sm';
        noteDiv.innerHTML = 
            <h6 class="mb-1 fw-bold" style="color: #0b2046;"> + (titleVal || 'Untitled Note') + </h6>
            <p class="mb-0 small text-muted"> + contentVal + </p>
        ;

        // Prepend to show newest on top
        savedNotesList.prepend(noteDiv);
        notesCount++;

        // Reset and hide form
        noteTitle.value = '';
        noteContent.value = '';
        noteForm.style.display = 'none';
        addNoteBtn.style.display = 'block';
        emptyNotesState.style.display = 'none';
    });
});
