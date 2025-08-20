import * as React from 'react';
import { Modal, ModalVariant, Button, ModalHeader, ModalBody, ModalFooter, Gallery, GalleryItem, Alert, AlertVariant } from '@patternfly/react-core';
import { DownloadIcon, CopyIcon, ExclamationTriangleIcon } from '@patternfly/react-icons';

interface ImagePreviewProps {
  content: string;
}

interface ImageModalState {
  isOpen: boolean;
  imageUrl: string;
  altText: string;
}

interface ImageError {
  url: string;
  message: string;
}

interface SecurityValidationResult {
  isValid: boolean;
  reason?: string;
}

interface ImageLoadState {
  loading: boolean;
  error: string | null;
  hasLoadError: boolean;
}

interface DetectedImage {
  url: string;
  alt: string;
  isValid: boolean;
  validationError?: string;
}

// Security constants
const ALLOWED_PROTOCOLS = ['https:', 'http:'];
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
// Commented out for now - uncomment and use in validateImageUrl if strict domain validation is needed
// const ALLOWED_DOMAINS = [
//   // Allow common image hosting services
//   'imgur.com', 'i.imgur.com',
//   'github.com', 'raw.githubusercontent.com',
//   'unsplash.com', 'images.unsplash.com',
//   'pexels.com', 'images.pexels.com',
//   'pixabay.com', 'cdn.pixabay.com',
//   'wikimedia.org', 'upload.wikimedia.org',
//   'githubusercontent.com',
//   // Add your trusted domains here
// ];

// Security validation functions
const validateImageUrl = (url: string): SecurityValidationResult => {
  try {
    const urlObj = new URL(url);
    
    // Check protocol
    if (!ALLOWED_PROTOCOLS.includes(urlObj.protocol)) {
      return { isValid: false, reason: 'Invalid protocol. Only HTTP and HTTPS are allowed.' };
    }
    
    // Check for localhost/private IP ranges (prevent SSRF)
    // Allow localhost URLs in development mode (when the page is also on localhost)
    const hostname = urlObj.hostname.toLowerCase();
    const isLocalDevelopment = window.location.hostname === 'localhost' || 
                               window.location.hostname === '127.0.0.1';
    
    // Allow localhost URLs if we're in local development
    if (!isLocalDevelopment) {
      if (
        hostname === 'localhost' ||
        hostname === '127.0.0.1' ||
        hostname.startsWith('192.168.') ||
        hostname.startsWith('10.') ||
        hostname.startsWith('172.') ||
        hostname === '0.0.0.0' ||
        hostname.includes('..') // Path traversal attempt
      ) {
        return { isValid: false, reason: 'Access to local/private networks is not allowed.' };
      }
    }
    
    // Check domain allowlist (optional - can be disabled for more permissive behavior)
    // Uncomment the following block to enable strict domain validation:
    /*
    const isAllowedDomain = ALLOWED_DOMAINS.some(domain => 
      hostname === domain || hostname.endsWith('.' + domain)
    );
    if (!isAllowedDomain) {
      return { isValid: false, reason: 'Domain not in allowlist.' };
    }
    */
    
    return { isValid: true };
  } catch (error) {
    return { isValid: false, reason: 'Invalid URL format.' };
  }
};

const validateImageType = async (url: string): Promise<SecurityValidationResult> => {
  try {
    const response = await fetch(url, { method: 'HEAD' });
    const contentType = response.headers.get('content-type');
    
    if (!contentType || !ALLOWED_IMAGE_TYPES.some(type => contentType.startsWith(type))) {
      return { isValid: false, reason: 'Invalid content type. Only image files are allowed.' };
    }
    
    const contentLength = response.headers.get('content-length');
    if (contentLength && parseInt(contentLength) > MAX_FILE_SIZE) {
      return { isValid: false, reason: 'File size exceeds limit (50MB max).' };
    }
    
    return { isValid: true };
  } catch (error) {
    return { isValid: false, reason: 'Unable to validate image.' };
  }
};

export const ImagePreview: React.FunctionComponent<ImagePreviewProps> = ({ content }) => {
  const [imageModal, setImageModal] = React.useState<ImageModalState>({
    isOpen: false,
    imageUrl: '',
    altText: ''
  });
  
  const [imageErrors, setImageErrors] = React.useState<Record<string, ImageError>>({});
  const [imageLoadStates, setImageLoadStates] = React.useState<Record<string, ImageLoadState>>({});
  const [clipboardError, setClipboardError] = React.useState<string | null>(null);

  // Detect images in content with security validation
  const detectedImages = React.useMemo(() => {
    const images: DetectedImage[] = [];
    
    // Detect markdown images: ![alt text](url)
    const markdownImageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    let match;
    while ((match = markdownImageRegex.exec(content)) !== null) {
      const url = match[2];
      const validation = validateImageUrl(url);
      images.push({
        url: url,
        alt: match[1] || 'Image',
        isValid: validation.isValid,
        validationError: validation.reason
      });
    }
    
    // Detect plain image URLs
    const imageUrlRegex = /https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|webp|svg)(\?[^\s]*)?/gi;
    while ((match = imageUrlRegex.exec(content)) !== null) {
      const url = match[0];
      // Check if this URL is already part of a markdown image
      const isMarkdownImage = images.some(img => img.url === url);
      if (!isMarkdownImage) {
        const validation = validateImageUrl(url);
        images.push({
          url: url,
          alt: 'Image',
          isValid: validation.isValid,
          validationError: validation.reason
        });
      }
    }
    
    return images;
  }, [content]);

  const handleImageClick = (url: string, alt: string) => {
    // Additional validation before opening modal
    const validation = validateImageUrl(url);
    if (!validation.isValid) {
      setImageErrors(prev => ({
        ...prev,
        [url]: { url, message: validation.reason || 'Invalid image URL' }
      }));
      return;
    }
    
    setImageModal({ isOpen: true, imageUrl: url, altText: alt });
  };
  
  const handleKeyDown = (event: React.KeyboardEvent, url: string, alt: string) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleImageClick(url, alt);
    }
  };
  
  const setImageLoadState = (url: string, state: Partial<ImageLoadState>) => {
    setImageLoadStates(prev => ({
      ...prev,
      [url]: { ...prev[url], ...state }
    }));
  };
  
  const handleImageError = (url: string, errorMessage: string) => {
    setImageErrors(prev => ({
      ...prev,
      [url]: { url, message: errorMessage }
    }));
    setImageLoadState(url, { hasLoadError: true, loading: false, error: errorMessage });
  };

  const handleCloseModal = () => {
    setImageModal({ isOpen: false, imageUrl: '', altText: '' });
    setClipboardError(null);
  };

  const handleDownload = async () => {
    try {
      // Validate URL before download
      const urlValidation = validateImageUrl(imageModal.imageUrl);
      if (!urlValidation.isValid) {
        setImageErrors(prev => ({
          ...prev,
          [imageModal.imageUrl]: { url: imageModal.imageUrl, message: urlValidation.reason || 'Invalid URL' }
        }));
        return;
      }
      
      // Validate content type and size
      const typeValidation = await validateImageType(imageModal.imageUrl);
      if (!typeValidation.isValid) {
        setImageErrors(prev => ({
          ...prev,
          [imageModal.imageUrl]: { url: imageModal.imageUrl, message: typeValidation.reason || 'Invalid image type' }
        }));
        return;
      }
      
      const response = await fetch(imageModal.imageUrl);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const contentLength = response.headers.get('content-length');
      if (contentLength && parseInt(contentLength) > MAX_FILE_SIZE) {
        throw new Error('File size exceeds limit (50MB max)');
      }
      
      const blob = await response.blob();
      
      // Double-check blob size
      if (blob.size > MAX_FILE_SIZE) {
        throw new Error('File size exceeds limit (50MB max)');
      }
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const filename = imageModal.imageUrl.split('/').pop()?.split('?')[0] || 'image';
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Error downloading image';
      console.error('Error downloading image:', error);
      setImageErrors(prev => ({
        ...prev,
        [imageModal.imageUrl]: { url: imageModal.imageUrl, message: errorMessage }
      }));
    }
  };

  const handleCopyUrl = async () => {
    try {
      setClipboardError(null);
      
      if (!navigator.clipboard) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = imageModal.imageUrl;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        return;
      }
      
      await navigator.clipboard.writeText(imageModal.imageUrl);
    } catch (error) {
      const errorMessage = 'Failed to copy URL to clipboard';
      console.error('Error copying to clipboard:', error);
      setClipboardError(errorMessage);
      
      // Try fallback method
      try {
        const textArea = document.createElement('textarea');
        textArea.value = imageModal.imageUrl;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        setClipboardError(null);
      } catch (fallbackError) {
        console.error('Fallback copy method also failed:', fallbackError);
      }
    }
  };

  // Filter out invalid images but show error messages for them
  const validImages = detectedImages.filter(img => img.isValid);
  const invalidImages = detectedImages.filter(img => !img.isValid);
  
  // If no valid images detected, show invalid image errors if any, otherwise return null
  if (validImages.length === 0 && invalidImages.length === 0) {
    return null;
  }

  return (
    <>
      <div style={{ marginTop: '12px' }}>
        {/* Show errors for invalid images */}
        {invalidImages.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            {invalidImages.map((image, index) => (
              <Alert
                key={`invalid-${image.url}-${index}`}
                variant={AlertVariant.warning}
                title="Invalid Image URL"
                style={{ marginBottom: '8px' }}
              >
                {image.validationError}: {image.url}
              </Alert>
            ))}
          </div>
        )}
        
        {/* Show errors for failed image loads */}
        {Object.values(imageErrors).map((error, index) => (
          <Alert
            key={`error-${error.url}-${index}`}
            variant={AlertVariant.danger}
            title="Image Load Error"
            style={{ marginBottom: '8px' }}
          >
            {error.message}: {error.url}
          </Alert>
        ))}
        
        {validImages.length > 0 && (
          <Gallery hasGutter minWidths={{ default: '300px', md: '400px' }}>
            {validImages.map((image, index) => {
              const loadState = imageLoadStates[image.url] || { loading: false, error: null, hasLoadError: false };
              const hasError = imageErrors[image.url] || loadState.hasLoadError;
              
              return (
                <GalleryItem key={`${image.url}-${index}`}>
                  <div
                    role="button"
                    tabIndex={0}
                    aria-label={`View image: ${image.alt}`}
                    style={{
                      cursor: 'pointer',
                      borderRadius: '8px',
                      overflow: 'hidden',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
                      transition: 'transform 0.2s, box-shadow 0.2s',
                      backgroundColor: 'var(--pf-v6-global--BackgroundColor--200)',
                      outline: 'none'
                    }}
                    onClick={() => handleImageClick(image.url, image.alt)}
                    onKeyDown={(e) => handleKeyDown(e, image.url, image.alt)}
                    onMouseOver={(e) => {
                      e.currentTarget.style.transform = 'scale(1.02)';
                      e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.15)';
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.transform = 'scale(1)';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.boxShadow = '0 0 0 2px var(--pf-v6-global--active-color--100)';
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                    }}
                  >
                    {hasError ? (
                      <div
                        style={{
                          width: '100%',
                          height: '300px',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'var(--pf-v6-global--danger-color--100)',
                          fontSize: '14px',
                          padding: '16px',
                          textAlign: 'center'
                        }}
                      >
                        <ExclamationTriangleIcon style={{ marginBottom: '8px', fontSize: '24px' }} />
                        <div>Failed to load image</div>
                        <div style={{ fontSize: '12px', marginTop: '4px', opacity: 0.8 }}>
                          {loadState.error || 'Unknown error'}
                        </div>
                      </div>
                    ) : (
                      <img
                        src={image.url}
                        alt={image.alt}
                        style={{
                          width: '100%',
                          height: '300px',
                          objectFit: 'cover',
                          display: 'block'
                        }}
                        onError={() => {
                          handleImageError(image.url, 'Failed to load image');
                        }}
                        onLoad={() => {
                          setImageLoadState(image.url, { loading: false, error: null, hasLoadError: false });
                        }}
                        onLoadStart={() => {
                          setImageLoadState(image.url, { loading: true, error: null, hasLoadError: false });
                        }}
                      />
                    )}
                  </div>
                </GalleryItem>
              );
            })}
          </Gallery>
        )}
      </div>
      
      <Modal
        variant={ModalVariant.large}
        isOpen={imageModal.isOpen}
        onClose={handleCloseModal}
        aria-labelledby="image-preview-modal"
        aria-describedby="image-preview-modal-description"
      >
        <ModalHeader
          title="Image Preview"
          labelId="image-preview-modal"
          descriptorId="image-preview-modal-description"
        />
        <ModalBody>
          {clipboardError && (
            <Alert
              variant={AlertVariant.danger}
              title="Clipboard Error"
              style={{ marginBottom: '16px' }}
            >
              {clipboardError}
            </Alert>
          )}
          
          {imageErrors[imageModal.imageUrl] && (
            <Alert
              variant={AlertVariant.danger}
              title="Image Error"
              style={{ marginBottom: '16px' }}
            >
              {imageErrors[imageModal.imageUrl].message}
            </Alert>
          )}
          
          <div style={{ textAlign: 'center' }}>
            <img
              src={imageModal.imageUrl}
              alt={imageModal.altText}
              style={{
                maxWidth: '100%',
                maxHeight: '60vh',
                objectFit: 'contain'
              }}
              onError={() => {
                handleImageError(imageModal.imageUrl, 'Failed to load image in preview');
              }}
            />
          </div>
        </ModalBody>
        <ModalFooter>
          <Button 
            key="download" 
            variant="secondary" 
            onClick={handleDownload} 
            icon={<DownloadIcon />}
            isDisabled={!!imageErrors[imageModal.imageUrl]}
          >
            Download
          </Button>
          <Button 
            key="copy" 
            variant="secondary" 
            onClick={handleCopyUrl} 
            icon={<CopyIcon />}
          >
            Copy URL
          </Button>
          <Button key="close" variant="primary" onClick={handleCloseModal}>
            Close
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
};