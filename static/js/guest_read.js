document.addEventListener('DOMContentLoaded', () => {
  const isAuthenticated = document.body.dataset.authenticated === 'true';
  const modal = document.getElementById('guestReadModal');
  const nameInput = document.getElementById('guestNameInput');
  const markBtn = document.getElementById('guestMarkReadBtn');
  const closeBtn = document.getElementById('guestCloseModalBtn');
  let currentUpdateId = null;
  let currentCountElement = null;

  // Only run on updates page
  if (!document.querySelector('.updates-list') && !document.querySelector('.updates-grid')) return;

  document.querySelectorAll('.update-item[data-update-id]').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', (e) => {
      // Ensure we always get the right read-count span
      currentCountElement = el.querySelector('.read-count');
      currentUpdateId = el.dataset.updateId;

      if (isAuthenticated) {
        sendMarkRead();
      } else {
        modal.classList.remove('hidden');
        nameInput.value = '';
        nameInput.focus();
      }
    });
  });

  closeBtn.addEventListener('click', (e) => {
    e.preventDefault();
    modal.classList.add('hidden');
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });

  markBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const guestName = nameInput.value.trim();
    if (!guestName) {
      alert('Please enter your name.');
      return;
    }
    sendMarkRead(guestName);
    modal.classList.add('hidden');
  });

  function sendMarkRead(guestName = null) {
    fetch('/mark_read', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        update_id: currentUpdateId,
        reader_name: guestName
      })
    })
    .then(r => {
      if (!r.ok) {
        throw new Error(`HTTP error! status: ${r.status}`);
      }
      return r.json();
    })
    .then(j => {
      if (j.status === 'success') {
        if (currentCountElement) {
          currentCountElement.textContent = `📖 ${j.read_count} reads`;
        }
        console.log('✅ Successfully marked as read');
      } else {
        console.error('❌ Error marking as read:', j.message);
        alert(j.message || 'Error marking as read');
      }
    })
    .catch(error => {
      console.error('❌ Network error marking as read:', error);
      alert('Network error. Please try again.');
    });
  }
});
