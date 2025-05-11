/**
 * Lazy Loading Component Manager
 * 
 * This script handles lazy loading of heavy components when they enter the viewport.
 * It helps improve initial page load time by deferring the loading of non-critical
 * components until they are about to become visible to the user.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Only proceed if IntersectionObserver is supported
  if ('IntersectionObserver' in window) {
    
    // Component definitions - add new lazy-loaded components here
    const componentDefinitions = [
      {
        selector: '.analytics-chart',
        module: '/static/js/charts/analytics-chart.js',
        callback: (element, module) => module.renderAnalyticsChart(element)
      },
      {
        selector: '.portfolio-visualizer',
        module: '/static/js/portfolio/visualizer.js',
        callback: (element, module) => module.initVisualizer(element)
      },
      {
        selector: '.opportunity-map',
        module: '/static/js/maps/opportunity-map.js',
        callback: (element, module) => module.renderMap(element)
      },
      {
        selector: '.skill-tree',
        module: '/static/js/skill-tree.js',
        callback: (element, module) => module.renderSkillTree(element)
      }
    ];
    
    // Create observers for each component type
    componentDefinitions.forEach(componentDef => {
      const elements = document.querySelectorAll(componentDef.selector);
      
      if (elements.length === 0) return; // Skip if no elements found
      
      const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          // When element is about to enter viewport
          if (entry.isIntersecting) {
            const element = entry.target;
            
            // Show loading indicator
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'component-loading';
            loadingIndicator.innerHTML = '<div class="loading-spinner"></div><span>Loading...</span>';
            element.appendChild(loadingIndicator);
            
            // Dynamically import the module
            import(componentDef.module)
              .then(module => {
                // Remove loading indicator
                element.querySelector('.component-loading')?.remove();
                
                // Initialize component
                componentDef.callback(element, module);
                
                // Stop observing this element
                observer.unobserve(element);
              })
              .catch(err => {
                console.error(`Error loading ${componentDef.module}:`, err);
                
                // Show error message
                const errorMessage = document.createElement('div');
                errorMessage.className = 'component-error';
                errorMessage.textContent = 'Failed to load component';
                element.querySelector('.component-loading')?.remove();
                element.appendChild(errorMessage);
              });
          }
        });
      }, {
        // Start loading when element is 200px before it enters viewport
        rootMargin: '200px 0px',
        threshold: 0.01
      });
      
      // Start observing the elements
      elements.forEach(element => {
        observer.observe(element);
      });
    });
    
    // Special handler for image galleries that need to be lazy loaded
    const imageGalleries = document.querySelectorAll('.lazy-image-gallery');
    if (imageGalleries.length > 0) {
      const galleryObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const gallery = entry.target;
            
            // Find all lazy images in this gallery
            const lazyImages = gallery.querySelectorAll('img[data-src]');
            lazyImages.forEach(img => {
              // Set the actual image source
              img.src = img.dataset.src;
              
              // If there's a srcset defined, set that too
              if (img.dataset.srcset) {
                img.srcset = img.dataset.srcset;
              }
              
              // Remove the data attributes
              img.removeAttribute('data-src');
              img.removeAttribute('data-srcset');
              
              // Add a class for any CSS transitions
              img.classList.add('loaded');
            });
            
            observer.unobserve(gallery);
          }
        });
      }, {
        rootMargin: '100px 0px'
      });
      
      imageGalleries.forEach(gallery => {
        galleryObserver.observe(gallery);
      });
    }
  } else {
    // Fallback for browsers that don't support IntersectionObserver
    console.warn('IntersectionObserver not supported - lazy loading disabled');
    
    // Load all modules immediately
    document.querySelectorAll('.analytics-chart, .portfolio-visualizer, .opportunity-map, .skill-tree')
      .forEach(element => {
        element.classList.add('no-lazy-load');
      });
    
    // Load all lazy images immediately
    document.querySelectorAll('img[data-src]').forEach(img => {
      img.src = img.dataset.src;
      if (img.dataset.srcset) img.srcset = img.dataset.srcset;
    });
  }
});