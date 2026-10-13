import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Image,
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';

export default function ScreenshotModal({ visible, imageUrl, images, onClose }) {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  const imageList =
    Array.isArray(images) && images.length > 0
      ? images
      : Array.isArray(imageUrl)
      ? imageUrl
      : imageUrl
      ? [imageUrl]
      : [];

  useEffect(() => {
    if (visible) {
      setCurrentIndex(0);
      setLoading(true);
      setLoadError(null);
    }
  }, [visible, imageUrl, images]);

  if (!visible || imageList.length === 0) return null;

  const currentUrl = imageList[currentIndex] || '';

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
      setLoading(true);
      setLoadError(null);
    }
  };

  const handleNext = () => {
    if (currentIndex < imageList.length - 1) {
      setCurrentIndex((prev) => prev + 1);
      setLoading(true);
      setLoadError(null);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        {/* Top Header Bar */}
        <View style={styles.topBar}>
          <View style={styles.titleCol}>
            <Text style={styles.headerTitle} numberOfLines={1}>
              📸 Project Screenshot Preview
            </Text>
            {imageList.length > 1 && (
              <Text style={styles.counterText}>
                Image {currentIndex + 1} of {imageList.length}
              </Text>
            )}
          </View>
          <TouchableOpacity
            style={styles.closeBtn}
            onPress={onClose}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            activeOpacity={0.8}
          >
            <Text style={styles.closeText}>✕ Close</Text>
          </TouchableOpacity>
        </View>

        {/* Content Body */}
        <View style={styles.imageWrapper}>
          {loading && !loadError && (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#38bdf8" />
              <Text style={styles.loadingText}>Fetching screenshot from relay...</Text>
            </View>
          )}

          {loadError ? (
            <View style={styles.errorContainer}>
              <Text style={styles.errorIcon}>⚠️</Text>
              <Text style={styles.errorTitle}>Could not load screenshot</Text>
              <Text style={styles.errorDetail}>
                Make sure your phone is connected to the same Wi-Fi network as your computer.
              </Text>
              <Text style={styles.errorUrl} numberOfLines={2}>
                {currentUrl}
              </Text>
              <TouchableOpacity
                style={styles.retryBtn}
                onPress={() => {
                  setLoadError(null);
                  setLoading(true);
                }}
              >
                <Text style={styles.retryText}>🔄 Retry Loading</Text>
              </TouchableOpacity>
            </View>
          ) : null}

          <Image
            key={currentUrl}
            source={{ uri: currentUrl }}
            style={[styles.image, loadError ? { display: 'none' } : null]}
            resizeMode="contain"
            onLoadStart={() => {
              setLoading(true);
              setLoadError(null);
            }}
            onLoadEnd={() => setLoading(false)}
            onError={(e) => {
              setLoading(false);
              setLoadError(e.nativeEvent?.error || 'Image network load failed');
            }}
          />
        </View>

        {/* Multi-Image Navigation Footer */}
        {imageList.length > 1 && (
          <View style={styles.navBar}>
            <TouchableOpacity
              style={[styles.navBtn, currentIndex === 0 ? styles.navBtnDisabled : null]}
              disabled={currentIndex === 0}
              onPress={handlePrev}
            >
              <Text style={[styles.navBtnText, currentIndex === 0 ? styles.navBtnTextDisabled : null]}>
                ◀ Previous
              </Text>
            </TouchableOpacity>

            <Text style={styles.navIndexText}>
              {currentIndex + 1} / {imageList.length}
            </Text>

            <TouchableOpacity
              style={[styles.navBtn, currentIndex === imageList.length - 1 ? styles.navBtnDisabled : null]}
              disabled={currentIndex === imageList.length - 1}
              onPress={handleNext}
            >
              <Text style={[styles.navBtnText, currentIndex === imageList.length - 1 ? styles.navBtnTextDisabled : null]}>
                Next ▶
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    justifyContent: 'space-between',
    paddingTop: 45,
    paddingBottom: 25,
    paddingHorizontal: 14,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  titleCol: {
    flex: 1,
  },
  headerTitle: {
    color: '#e2e8f0',
    fontSize: 14,
    fontWeight: '700',
  },
  counterText: {
    color: '#38bdf8',
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
  },
  closeBtn: {
    backgroundColor: '#3b82f6',
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 8,
    marginLeft: 10,
  },
  closeText: {
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: 13,
  },
  imageWrapper: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
    marginTop: 8,
  },
  loadingContainer: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2,
  },
  loadingText: {
    marginTop: 10,
    color: '#94a3b8',
    fontSize: 12,
  },
  errorContainer: {
    padding: 20,
    backgroundColor: '#1e293b',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ef4444',
    alignItems: 'center',
    maxWidth: '90%',
  },
  errorIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  errorTitle: {
    color: '#f87171',
    fontWeight: 'bold',
    fontSize: 15,
    marginBottom: 6,
  },
  errorDetail: {
    color: '#94a3b8',
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 10,
    lineHeight: 16,
  },
  errorUrl: {
    color: '#64748b',
    fontSize: 10,
    textAlign: 'center',
    marginBottom: 12,
  },
  retryBtn: {
    backgroundColor: '#0284c7',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  retryText: {
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  image: {
    width: '100%',
    height: '100%',
  },
  navBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#334155',
  },
  navBtn: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#475569',
  },
  navBtnDisabled: {
    opacity: 0.35,
  },
  navBtnText: {
    color: '#38bdf8',
    fontWeight: '700',
    fontSize: 12,
  },
  navBtnTextDisabled: {
    color: '#64748b',
  },
  navIndexText: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
  },
});
