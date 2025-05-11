/**
 * Test script for fetchWithRetry functionality 
 * 
 * This script tests the fetchWithRetry function with simulated failures
 * to demonstrate the retry mechanism, timeout handling, and retry events.
 */

// Mock the fetchWithRetry function from opportunities.html
async function fetchWithRetry(url, options = {}, retries = 2, backoff = 300, attempt = 1) {
    try {
        console.log(`[fetchWithRetry] Attempt #${attempt} for ${url}`);
        
        // For testing, we'll simulate a success after 2 tries
        if (url.includes('simulate-success-after-retries') && attempt < 3) {
            throw new Error('Simulated failure');
        }
        
        // For testing, we'll simulate a permanent failure
        if (url.includes('simulate-permanent-failure')) {
            throw new Error('Simulated permanent failure');
        }
        
        // For testing timeouts
        if (url.includes('simulate-timeout')) {
            await new Promise(r => setTimeout(r, options.timeout ? options.timeout + 100 : 10100));
            throw new Error('Request timed out');
        }
        
        // Simulate a real fetch
        const fetchPromise = fetch(url, {
            ...options,
            credentials: 'same-origin'
        });
        
        const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Request timed out')), options.timeout || 10000)
        );
        
        const res = await Promise.race([fetchPromise, timeoutPromise]);
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        // Try to parse as JSON first
        const text = await res.text();
        try {
            return JSON.parse(text);
        } catch (e) {
            // If not JSON, return text
            return text;
        }
    } catch (err) {
        console.error(`Fetch error (retries left: ${retries}):`, err.message);
        
        if (retries > 0) {
            // Wait with exponential backoff
            await new Promise(r => setTimeout(r, backoff));
            
            // Emit a custom event to update UI with retry progress
            const retryEvent = new CustomEvent('fetchRetry', {
                detail: {
                    url: url,
                    retries: retries,
                    attempt: attempt,
                    error: err.message,
                    backoff: backoff
                }
            });
            document.dispatchEvent(retryEvent);
            
            console.log(`Retrying fetch to ${url} (${retries} retries left, attempt ${attempt + 1}, next backoff: ${backoff * 2}ms)`);
            
            // Show retry UI message if this were a real application
            console.log(`UI would show: Retrying connection (attempt ${attempt + 1} of ${attempt + retries})...`);
            
            return fetchWithRetry(url, options, retries - 1, backoff * 2, attempt + 1);
        }
        throw err;
    }
}

// Set up a test to capture the retry events
document.addEventListener('fetchRetry', (e) => {
    const { url, retries, attempt, error, backoff } = e.detail;
    console.log(`[Event] fetchRetry detected:`, {
        url,
        retriesLeft: retries,
        currentAttempt: attempt,
        error,
        nextBackoff: backoff * 2
    });
});

// Test functions
async function testSuccessfulFetch() {
    console.log('=== Testing successful fetch ===');
    try {
        // Use a reliable endpoint that should succeed
        const result = await fetchWithRetry('/static/js/test_fetch_retry.js', {
            timeout: 5000
        }, 2, 300);
        console.log('Success! Response length:', result.length);
        return true;
    } catch (err) {
        console.error('Test failed:', err);
        return false;
    }
}

async function testRetryWithSuccess() {
    console.log('=== Testing retry with eventual success ===');
    try {
        // This URL will fail twice then succeed
        const result = await fetchWithRetry('/simulate-success-after-retries', {
            timeout: 1000
        }, 3, 100);
        console.log('Success after retries!');
        return true;
    } catch (err) {
        console.error('Test failed:', err);
        return false;
    }
}

async function testRetryWithFailure() {
    console.log('=== Testing retry with permanent failure ===');
    try {
        // This URL will always fail
        const result = await fetchWithRetry('/simulate-permanent-failure', {
            timeout: 1000
        }, 2, 100);
        console.log('Unexpected success!');
        return false;
    } catch (err) {
        console.log('Expected failure occurred:', err.message);
        return true;
    }
}

async function testTimeout() {
    console.log('=== Testing timeout handling ===');
    try {
        // This URL will time out
        const result = await fetchWithRetry('/simulate-timeout', {
            timeout: 1000 // Short timeout
        }, 2, 100);
        console.log('Unexpected success!');
        return false;
    } catch (err) {
        console.log('Expected timeout occurred:', err.message);
        return true;
    }
}

// Run all tests
async function runAllTests() {
    console.log('Starting fetchWithRetry tests...');
    
    const results = {
        successfulFetch: await testSuccessfulFetch(),
        retryWithSuccess: await testRetryWithSuccess(),
        retryWithFailure: await testRetryWithFailure(),
        timeout: await testTimeout()
    };
    
    console.log('=== Test Results ===');
    console.table(results);
    console.log('Tests completed!');
}

// Automatically run when loaded
window.addEventListener('load', runAllTests);