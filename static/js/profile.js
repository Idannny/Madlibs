
const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

function viewStory(storyId) {
    window.location.href = `/story/${storyId}`;
}



