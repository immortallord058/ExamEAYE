// Webcam utility functions

export const startWebcam = async (
  videoElement: HTMLVideoElement
): Promise<MediaStream> => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user',
      },
      audio: false,
    });

    videoElement.srcObject = stream;
    await videoElement.play();

    return stream;
  } catch (error) {
    console.error('Webcam access error:', error);
    throw new Error('Failed to access webcam. Please grant camera permissions.');
  }
};

export const stopWebcam = (stream: MediaStream | null): void => {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }
};

export const captureFrame = (videoElement: HTMLVideoElement): string => {
  const canvas = document.createElement('canvas');
  canvas.width = videoElement.videoWidth;
  canvas.height = videoElement.videoHeight;

  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Failed to get canvas context');

  ctx.drawImage(videoElement, 0, 0);

  // Return base64 encoded image
  return canvas.toDataURL('image/jpeg', 0.8);
};

export const checkCameraPermissions = async (): Promise<boolean> => {
  try {
    const result = await navigator.permissions.query({ name: 'camera' as PermissionName });
    return result.state === 'granted';
  } catch {
    // Fallback: try to access camera
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      stream.getTracks().forEach((track) => track.stop());
      return true;
    } catch {
      return false;
    }
  }
};
