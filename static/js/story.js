function shareStory() {
    // Create a temporary textarea to hold the story content
    const textArea = document.createElement('textarea');
    const storyContent = `Check out my AI-generated Mad Lib story!\n\n${document.querySelector('.story-text p').textContent}\n\nCreate your own at [Your Website URL]`;
    
    textArea.value = storyContent;
    document.body.appendChild(textArea);
    textArea.select();
    
    try {
        document.execCommand('copy');
        alert('Story copied to clipboard! You can now share it with others.');
    } catch (err) {
        console.error('Failed to copy story:', err);
        alert('Failed to copy story to clipboard.');
    } finally {
        document.body.removeChild(textArea);
    }
}