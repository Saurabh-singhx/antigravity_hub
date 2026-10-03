import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Image,
  StatusBar,
  Vibration,
  Platform,
  AppState,
  Alert,
  PermissionsAndroid,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { NeoColors, NeoStyles } from './src/theme/neomorphism';
import TodayPrepScreen from './src/screens/TodayPrepScreen';
import ArchiveScreen from './src/screens/ArchiveScreen';
import AlertsScreen from './src/screens/AlertsScreen';
import StatusScreen from './src/screens/StatusScreen';
import HubSettingsModal from './src/components/HubSettingsModal';
import ScreenshotModal from './src/components/ScreenshotModal';
import OtpModal from './src/components/OtpModal';

// Ensure system notifications pop up as banners with sound when received
try {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  });
} catch (e) {
  console.log('Notifications.setNotificationHandler note:', e);
}

const DEFAULT_HUB_PORT = '8765';
const DEFAULT_HUB_IP = '192.168.31.210';
const DEFAULT_HUB_URL = `http://${DEFAULT_HUB_IP}:${DEFAULT_HUB_PORT}`;

const cleanHubUrl = (input) => {
  if (!input || !input.trim()) return DEFAULT_HUB_URL;
  let str = input.trim();
  if (!/^https?:\/\//i.test(str)) {
    str = 'http://' + str;
  }
  const withoutProto = str.replace(/^https?:\/\//i, '');
  if (!withoutProto.includes(':')) {
    str = str.replace(/\/+$/, '') + `:${DEFAULT_HUB_PORT}`;
  }
  return str.replace(/\/+$/, '');
};

const getInitialHubUrl = () => {
  try {
    const hostUri = Constants?.expoConfig?.hostUri || Constants?.manifest?.debuggerHost || '';
    if (hostUri) {
      const host = hostUri.split(':')[0];
      if (host && host !== 'localhost' && host !== '127.0.0.1') {
        return `http://${host}:${DEFAULT_HUB_PORT}`;
      }
    }
  } catch (e) {
    console.log('Error determining host IP:', e);
  }
  return DEFAULT_HUB_URL;
};

export default function App() {
  return (
    <SafeAreaProvider>
      <MainContainer />
    </SafeAreaProvider>
  );
}

function MainContainer() {
  const [hubUrl, setHubUrl] = useState(getInitialHubUrl());
  const [hubToken, setHubToken] = useState('');
  const [connected, setConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('PREP'); // 'PREP', 'ARCHIVE', 'ALERTS', 'STATUS'

  // Modals
  const [ipModalVisible, setIpModalVisible] = useState(false);
  const [selectedScreenshot, setSelectedScreenshot] = useState(null);
  const [activeOtpAction, setActiveOtpAction] = useState(null);
  const [submittingOtp, setSubmittingOtp] = useState(false);

  // Data States
  const [dailyData, setDailyData] = useState({ items: [], slot_progress: {}, active_slot_id: null });
  const [notifications, setNotifications] = useState([]);
  const [loadingDaily, setLoadingDaily] = useState(false);
  const [loadingNotifs, setLoadingNotifs] = useState(false);

  const wsRef = useRef(null);
  const retryTimeoutRef = useRef(null);
  const pushTokenRef = useRef(null);
  const seenNotifIdsRef = useRef(new Set());

  // Load saved Hub URL and Token
  useEffect(() => {
    Promise.all([
      AsyncStorage.getItem('antigravity_hub_url'),
      AsyncStorage.getItem('antigravity_hub_token'),
    ])
      .then(([savedUrl, savedToken]) => {
        if (savedUrl && savedUrl.trim()) {
          setHubUrl(cleanHubUrl(savedUrl));
        }
        if (savedToken && savedToken.trim()) {
          setHubToken(savedToken.trim());
        }
      })
      .catch((e) => console.log('AsyncStorage load error:', e));
  }, []);

  // Helper to generate auth headers
  const getAuthHeaders = (token = hubToken) => ({
    'Content-Type': 'application/json',
    ...(token ? { 'X-Hub-Token': token, 'Authorization': `Bearer ${token}` } : {}),
  });

  // Fetch Daily QnA feed (resets daily on mobile)
  const fetchDailyFeed = async (targetUrl = hubUrl, targetToken = hubToken) => {
    try {
      setLoadingDaily(true);
      const res = await fetch(`${targetUrl}/api/qna/daily`, {
        headers: getAuthHeaders(targetToken),
      });
      if (res.ok) {
        const json = await res.json();
        setDailyData(json);
        setConnected(true);
      }
    } catch (e) {
      console.log('Error fetching daily QnA:', e.message);
    } finally {
      setLoadingDaily(false);
    }
  };

  // Fetch Live Notifications
  const fetchNotifications = async (targetUrl = hubUrl, targetToken = hubToken) => {
    try {
      setLoadingNotifs(true);
      const res = await fetch(`${targetUrl}/api/notifications?limit=40`, {
        headers: getAuthHeaders(targetToken),
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
        if (Array.isArray(data)) {
          data.forEach((n) => {
            if (n && n.id) seenNotifIdsRef.current.add(n.id);
          });
        }
        setConnected(true);
      }
    } catch (e) {
      console.log('Error fetching notifications:', e.message);
    } finally {
      setLoadingNotifs(false);
    }
  };

  const refreshAll = (targetUrl = hubUrl, targetToken = hubToken) => {
    fetchDailyFeed(targetUrl, targetToken);
    fetchNotifications(targetUrl, targetToken);
  };

  // Setup Push & System Notifications
  useEffect(() => {
    const setupNotifications = async () => {
      try {
        if (Platform.OS === 'android') {
          // Explicitly request Android 13+ runtime notification permission
          if (Platform.Version >= 33) {
            try {
              await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS);
            } catch (pErr) {}
          }

          // Register high-priority notification channel for status bar
          await Notifications.setNotificationChannelAsync('default', {
            name: 'Antigravity Hub Alerts',
            importance: Notifications.AndroidImportance.MAX,
            vibrationPattern: [0, 250, 250, 250],
            lightColor: '#4f46e5',
            sound: 'default',
            enableVibrate: true,
            showBadge: true,
            lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
            bypassDnd: true,
          });
        }

        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;
        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }

        if (finalStatus === 'granted') {
          const tokenData = await Notifications.getExpoPushTokenAsync().catch(() => null);
          if (tokenData && tokenData.data) {
            pushTokenRef.current = tokenData.data;
            fetch(`${hubUrl}/api/devices/register`, {
              method: 'POST',
              headers: getAuthHeaders(),
              body: JSON.stringify({
                device_id: 'android_' + (Platform.OS || 'mobile'),
                device_name: 'Android Mobile',
                push_token: tokenData.data,
                platform: Platform.OS || 'android',
              }),
            }).catch(() => {});
          }
        }
      } catch (err) {
        console.log('Push notification config note:', err);
      }
    };

    setupNotifications();
  }, [hubUrl, hubToken]);

  // Connect WebSocket for 0ms Live Updates
  useEffect(() => {
    refreshAll();

    let socket;
    let isMounted = true;

    const connectWebSocket = () => {
      if (!isMounted) return;
      const tokenQuery = hubToken ? `?token=${encodeURIComponent(hubToken)}` : '';
      const wsUrl = hubUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/notifications' + tokenQuery;

      try {
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isMounted) return;
          setConnected(true);
          console.log('Connected to WebSocket at', hubUrl);
        };

        socket.onmessage = async (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);

            // Handle QnA update event
            if (data.event === 'qna_updated') {
              fetchDailyFeed(hubUrl, hubToken);
              return;
            }

            // Normal notification payload
            const payload = data;
            const notifId = payload.id;

            // Prevent duplicate banners and alerts for already-seen notifications
            if (notifId && seenNotifIdsRef.current.has(notifId)) {
              return;
            }
            if (notifId) {
              seenNotifIdsRef.current.add(notifId);
            }

            if (Platform.OS !== 'web') {
              Vibration.vibrate(payload.level === 'critical' ? [0, 250, 100, 250] : 100);
            }
            setNotifications((prev) => [payload, ...prev.filter((n) => n.id !== notifId)]);

            // If action is requested (e.g. OTP prompt), pop up the dialog!
            if (payload.action && payload.action.status === 'pending') {
              if (payload.action.action_type === 'input') {
                setActiveOtpAction(payload.action);
              }
            }

            // Trigger local system notification banner on Android notification bar
            try {
              await Notifications.scheduleNotificationAsync({
                content: {
                  title: payload.title || 'Antigravity Hub',
                  body: payload.message || '',
                  sound: 'default',
                  priority: Notifications.AndroidNotificationPriority.MAX,
                  channelId: 'default',
                  color: '#4f46e5',
                  vibrate: [0, 250, 250, 250],
                  data: payload,
                },
                trigger: null,
              });
            } catch (notifErr) {
              console.log('Error scheduling banner on notification bar:', notifErr);
            }
          } catch (e) {
            console.log('WS parse error:', e);
          }
        };

        socket.onclose = () => {
          if (!isMounted) return;
          setConnected(false);
          retryTimeoutRef.current = setTimeout(connectWebSocket, 3500);
        };

        socket.onerror = () => {
          if (!isMounted) return;
          setConnected(false);
          if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
          retryTimeoutRef.current = setTimeout(connectWebSocket, 4000);
        };
      } catch (err) {
        console.log('WS error:', err);
      }
    };

    connectWebSocket();

    // Reconnect and sync when app transitions from background to active
    const appStateSub = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') {
        refreshAll(hubUrl, hubToken);
        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
          connectWebSocket();
        }
      }
    });

    return () => {
      isMounted = false;
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      if (socket) socket.close();
      if (appStateSub && appStateSub.remove) appStateSub.remove();
    };
  }, [hubUrl, hubToken]);

  // Handle responding to Action (OTP / Approve / Skip)
  const handleSubmitAction = async (actionId, value) => {
    if (!value || !value.trim()) {
      Alert.alert('Required', 'Please enter a value.');
      return;
    }

    try {
      const notif = notifications.find(
        (n) => n.action_id === actionId || (n.action && n.action.action_id === actionId)
      );
      const actionSecret = notif?.action?.action_secret || null;

      const res = await fetch(`${hubUrl}/api/actions/${actionId}/respond`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          action_id: actionId,
          response_value: value.trim(),
          action_secret: actionSecret,
        }),
      });

      if (res.ok) {
        setNotifications((prev) =>
          prev.map((n) => {
            if (n.action_id === actionId || (n.action && n.action.action_id === actionId)) {
              return {
                ...n,
                action_status: 'resolved',
                action_response: value.trim(),
                action: n.action ? { ...n.action, status: 'resolved', response_value: value.trim() } : null,
              };
            }
            return n;
          })
        );
        setActiveOtpAction(null);
        Alert.alert('Delivered', 'Action response sent to Antigravity CLI.');
      } else {
        Alert.alert('Error', 'Could not deliver response to CLI.');
      }
    } catch (err) {
      Alert.alert('Connection Error', err.message);
    }
  };

  const handleDismissNotification = async (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    fetch(`${hubUrl}/api/notifications/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    }).catch(() => {});
  };

  const handleSaveHubConfig = (newUrl, newToken) => {
    const cleanedUrl = cleanHubUrl(newUrl);
    const cleanedToken = (newToken || '').trim();
    setHubUrl(cleanedUrl);
    setHubToken(cleanedToken);
    AsyncStorage.setItem('antigravity_hub_url', cleanedUrl).catch(() => {});
    AsyncStorage.setItem('antigravity_hub_token', cleanedToken).catch(() => {});
    setIpModalVisible(false);
    refreshAll(cleanedUrl, cleanedToken);
  };

  const pendingActionCount = notifications.filter((n) => {
    const act = n.action_id || (n.action && n.action.action_id);
    return Boolean(act && (n.action_status === 'pending' || (n.action && n.action.status === 'pending')));
  }).length;

  const triggerLocalBanner = async () => {
    try {
      if (Platform.OS === 'android') {
        if (Platform.Version >= 33) {
          try {
            await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS);
          } catch (p) {}
        }
        await Notifications.setNotificationChannelAsync('default', {
          name: 'Antigravity Hub Alerts',
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
          lightColor: '#4f46e5',
          sound: 'default',
          enableVibrate: true,
          showBadge: true,
          lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
          bypassDnd: true,
        });
      }

      await Notifications.scheduleNotificationAsync({
        content: {
          title: '🎯 Interview Prep (Live Banner)',
          body: 'Top Question: "How do you diagnose and resolve a 504 Gateway Timeout in microservices?" Sourced from Engineering Blogs Digest. Tap to open!',
          sound: 'default',
          priority: Notifications.AndroidNotificationPriority.MAX,
          channelId: 'default',
          color: '#4f46e5',
          vibrate: [0, 250, 250, 250],
        },
        trigger: null,
      });
      Alert.alert('Banner Dispatched', 'Check your phone top notification bar / notification shade!');
    } catch (e) {
      Alert.alert('Error', e.message);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor={NeoColors.background} />

      {/* Top Neomorphic Navigation Header */}
      <View style={styles.topHeader}>
        <View style={styles.brandRow}>
          <Image source={require('./assets/logo.png')} style={styles.brandLogo} />
          <View>
            <Text style={styles.brandTitle}>ANTIGRAVITY</Text>
            <View style={styles.statusPill}>
              <View style={[styles.statusDot, { backgroundColor: connected ? '#10b981' : '#ef4444' }]} />
              <Text style={styles.statusText}>{connected ? 'Online' : 'Offline'}</Text>
            </View>
          </View>
        </View>

        <View style={styles.topBtnRow}>
          <TouchableOpacity
            onPress={triggerLocalBanner}
            style={styles.headerBtn}
          >
            <Text style={styles.headerBtnText}>🔔 Banner</Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => setIpModalVisible(true)}
            style={styles.headerBtn}
          >
            <Text style={styles.headerBtnText}>⚙️ IP</Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={refreshAll}
            style={styles.headerBtn}
          >
            <Text style={styles.headerBtnText}>🔄</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Neomorphic Tab Bar */}
      <View style={styles.navTabBar}>
        {[
          { key: 'PREP', label: '🎯 Prep', badge: dailyData.items.length },
          { key: 'ARCHIVE', label: '📚 Archive' },
          { key: 'ALERTS', label: '🔔 Alerts', badge: pendingActionCount },
          { key: 'STATUS', label: '⚙️ Status' },
        ].map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <TouchableOpacity
              key={tab.key}
              onPress={() => setActiveTab(tab.key)}
              style={[
                styles.navTabBtn,
                isActive ? styles.navTabBtnActive : styles.navTabBtnInactive,
              ]}
            >
              <Text
                style={[
                  styles.navTabText,
                  isActive && styles.navTabTextActive,
                ]}
              >
                {tab.label}
              </Text>
              {tab.badge > 0 ? (
                <View style={[styles.navBadge, isActive ? styles.navBadgeActive : styles.navBadgeInactive]}>
                  <Text style={[styles.navBadgeText, isActive ? styles.navBadgeTextActive : styles.navBadgeTextInactive]}>
                    {tab.badge}
                  </Text>
                </View>
              ) : null}
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Main Screen Body */}
      <View style={styles.screenContainer}>
        {activeTab === 'PREP' && (
          <TodayPrepScreen
            dailyData={dailyData}
            loading={loadingDaily}
            onRefresh={() => fetchDailyFeed(hubUrl, hubToken)}
            hubUrl={hubUrl}
            hubToken={hubToken}
            connected={connected}
          />
        )}

        {activeTab === 'ARCHIVE' && (
          <ArchiveScreen hubUrl={hubUrl} hubToken={hubToken} />
        )}

        {activeTab === 'ALERTS' && (
          <AlertsScreen
            notifications={notifications}
            loading={loadingNotifs}
            onRefresh={() => fetchNotifications(hubUrl, hubToken)}
            onDismiss={handleDismissNotification}
            onSubmitAction={handleSubmitAction}
            onOpenScreenshot={(url) => {
              let finalUrl = url;
              if (finalUrl && hubToken && !finalUrl.includes('token=')) {
                finalUrl += (finalUrl.includes('?') ? '&' : '?') + `token=${encodeURIComponent(hubToken)}`;
              }
              setSelectedScreenshot(finalUrl);
            }}
          />
        )}

        {activeTab === 'STATUS' && (
          <StatusScreen
            hubUrl={hubUrl}
            hubToken={hubToken}
            connected={connected}
            onOpenSettings={() => setIpModalVisible(true)}
            onRefresh={() => refreshAll(hubUrl, hubToken)}
          />
        )}
      </View>

      {/* IP & Security Settings Modal */}
      <HubSettingsModal
        visible={ipModalVisible}
        currentUrl={hubUrl}
        currentToken={hubToken}
        onSave={handleSaveHubConfig}
        onClose={() => setIpModalVisible(false)}
      />

      {/* Fullscreen Screenshot Modal */}
      <ScreenshotModal
        visible={Boolean(selectedScreenshot)}
        imageUrl={selectedScreenshot}
        onClose={() => setSelectedScreenshot(null)}
      />

      {/* OTP / 2FA Action Modal */}
      <OtpModal
        visible={Boolean(activeOtpAction)}
        action={activeOtpAction}
        loading={submittingOtp}
        onSubmit={async (actId, val) => {
          setSubmittingOtp(true);
          try {
            await handleSubmitAction(actId, val);
          } finally {
            setSubmittingOtp(false);
          }
        }}
        onCancel={() => setActiveOtpAction(null)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: NeoColors.background,
  },
  topHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 6,
    paddingBottom: 8,
    backgroundColor: NeoColors.background,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  brandLogo: {
    width: 32,
    height: 32,
    borderRadius: 8,
  },
  brandTitle: {
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 0.5,
    color: NeoColors.textPrimary,
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 1,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 4,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
    color: NeoColors.textMuted,
  },
  topBtnRow: {
    flexDirection: 'row',
    gap: 8,
  },
  headerBtn: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#c7d3e3',
  },
  headerBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: NeoColors.textPrimary,
  },
  navTabBar: {
    flexDirection: 'row',
    backgroundColor: '#dce5f2',
    marginHorizontal: 14,
    marginVertical: 6,
    padding: 3,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ccd7e6',
  },
  navTabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 7,
    borderRadius: 9,
  },
  navTabBtnActive: {
    backgroundColor: '#ffffff',
    shadowColor: '#8a9ab0',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3,
    elevation: 3,
  },
  navTabBtnInactive: {
    backgroundColor: 'transparent',
  },
  navTabText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#64748b',
  },
  navTabTextActive: {
    color: '#4f46e5',
  },
  navBadge: {
    marginLeft: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 8,
  },
  navBadgeActive: {
    backgroundColor: '#4f46e5',
  },
  navBadgeInactive: {
    backgroundColor: '#cbd5e1',
  },
  navBadgeText: {
    fontSize: 9,
    fontWeight: '800',
  },
  navBadgeTextActive: {
    color: '#ffffff',
  },
  navBadgeTextInactive: {
    color: '#334155',
  },
  screenContainer: {
    flex: 1,
  },
});
