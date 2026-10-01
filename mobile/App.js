import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  TouchableOpacity,
  TextInput,
  Modal,
  Image,
  StatusBar,
  ActivityIndicator,
  Alert,
  Vibration,
  Platform,
  PermissionsAndroid,
  AppState,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Ensure system notifications pop up as banners with sound when received
try {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    }),
  });
} catch (e) {
  console.log('Notifications.setNotificationHandler error:', e);
}

const DEFAULT_HUB_PORT = '8765';
const DEFAULT_HUB_IP = '192.168.31.210';
const DEFAULT_HUB_URL = `http://${DEFAULT_HUB_IP}:${DEFAULT_HUB_PORT}`;

// Clean and normalize Hub URL
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

// Formats UTC created_at into local device timezone with friendly relative or readable time
export const formatNotificationTime = (dateStr) => {
  if (!dateStr) return 'Just now';
  try {
    let clean = dateStr.trim();
    if (!clean.includes('T')) clean = clean.replace(' ', 'T');
    if (!clean.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(clean)) clean += 'Z';
    const date = new Date(clean);
    if (isNaN(date.getTime())) return dateStr;

    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSec < 45) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;

    const isToday =
      date.getDate() === now.getDate() &&
      date.getMonth() === now.getMonth() &&
      date.getFullYear() === now.getFullYear();

    const timeStr = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });

    if (isToday) {
      return timeStr;
    }

    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday =
      date.getDate() === yesterday.getDate() &&
      date.getMonth() === yesterday.getMonth() &&
      date.getFullYear() === yesterday.getFullYear();

    if (isYesterday) {
      return `Yesterday, ${timeStr}`;
    }

    const dateFormatted = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    return `${dateFormatted}, ${timeStr}`;
  } catch (e) {
    return dateStr;
  }
};

// Automatically detect host computer's IP from Expo connection or use current Wi-Fi IP
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
      <MainScreen />
    </SafeAreaProvider>
  );
}

function MainScreen() {
  const [hubUrl, setHubUrl] = useState(getInitialHubUrl());
  const [ipModalVisible, setIpModalVisible] = useState(false);
  const [tempIp, setTempIp] = useState(getInitialHubUrl());

  // Load persisted Hub URL and auto-clear setting from local storage on launch
  useEffect(() => {
    AsyncStorage.getItem('antigravity_hub_url')
      .then((saved) => {
        if (saved && saved.trim()) {
          const cleaned = cleanHubUrl(saved);
          setHubUrl(cleaned);
          setTempIp(cleaned);
        }
      })
      .catch((e) => console.log('AsyncStorage load error:', e));

    AsyncStorage.getItem('antigravity_auto_clear_mins')
      .then((saved) => {
        if (saved !== null && saved !== undefined) {
          const parsed = parseInt(saved, 10);
          if (!isNaN(parsed)) {
            setAutoClearMinutes(parsed);
          }
        }
      })
      .catch((e) => console.log('AsyncStorage autoClear load error:', e));
  }, []);

  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting'); // 'connected' | 'connecting' | 'error'
  const [connectionError, setConnectionError] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [activeTab, setActiveTab] = useState('ALL'); // ALL, JOB_APPLY, ACTIONS, ERRORS
  const [loading, setLoading] = useState(false);

  // Active action input states (keyed by action_id)
  const [actionInputs, setActionInputs] = useState({});
  const [submittingAction, setSubmittingAction] = useState({});

  // Fullscreen screenshot modal
  const [selectedImage, setSelectedImage] = useState(null);

  const wsRef = useRef(null);
  const retryTimeoutRef = useRef(null);
  const pushTokenRef = useRef(null);

  // Cleanup & auto-clear state
  const [cleanupModalVisible, setCleanupModalVisible] = useState(false);
  const [autoClearMinutes, setAutoClearMinutes] = useState(15); // Auto-clear routine alerts older than 15m

  const updateAutoClearMinutes = (mins) => {
    setAutoClearMinutes(mins);
    AsyncStorage.setItem('antigravity_auto_clear_mins', String(mins)).catch(() => {});
    if (mins > 0) {
      // Immediately trigger backend deletion
      fetch(`${hubUrl}/api/notifications?older_than_minutes=${mins}&scope=non_critical`, { method: 'DELETE' }).catch(() => {});
      // Prune local state immediately
      const cutoff = Date.now() - mins * 60 * 1000;
      setNotifications((prev) =>
        prev.filter((n) => {
          const isCritical =
            n.level === 'critical' ||
            n.level === 'error' ||
            (n.action_id && (n.action_status === 'pending' || n.action?.status === 'pending'));
          if (isCritical) return true;
          if (!n.created_at) return true;
          const cleanDateStr = n.created_at.replace(' ', 'T') + (n.created_at.includes('Z') ? '' : 'Z');
          const ts = new Date(cleanDateStr).getTime();
          if (isNaN(ts)) return true;
          return ts > cutoff;
        })
      );
    }
  };

  // Auto-prune routine alerts older than autoClearMinutes and sync with backend
  useEffect(() => {
    if (!autoClearMinutes || autoClearMinutes <= 0) return;

    const pruneOld = () => {
      const cutoff = Date.now() - autoClearMinutes * 60 * 1000;
      setNotifications((prev) =>
        prev.filter((n) => {
          const isCritical =
            n.level === 'critical' ||
            n.level === 'error' ||
            (n.action_id && (n.action_status === 'pending' || n.action?.status === 'pending'));
          if (isCritical) return true;

          if (!n.created_at) return true;
          const cleanDateStr = n.created_at.replace(' ', 'T') + (n.created_at.includes('Z') ? '' : 'Z');
          const ts = new Date(cleanDateStr).getTime();
          if (isNaN(ts)) return true;
          return ts > cutoff;
        })
      );
      // Persistently delete from backend so items never reappear on pull-refresh or new notification
      fetch(`${hubUrl}/api/notifications?older_than_minutes=${autoClearMinutes}&scope=non_critical`, {
        method: 'DELETE',
      }).catch(() => {});
    };

    const interval = setInterval(pruneOld, 15000);
    return () => clearInterval(interval);
  }, [autoClearMinutes, hubUrl]);

  const dismissNotification = async (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    try {
      fetch(`${hubUrl}/api/notifications/${id}`, { method: 'DELETE' }).catch(() => {});
    } catch (e) {}
  };

  const handleClearNotifications = async (scope = 'all') => {
    try {
      if (scope === 'non_critical') {
        setNotifications((prev) =>
          prev.filter(
            (n) =>
              n.level === 'critical' ||
              n.level === 'error' ||
              (n.action_id && (n.action_status === 'pending' || n.action?.status === 'pending'))
          )
        );
      } else {
        setNotifications([]);
      }
      setCleanupModalVisible(false);
      fetch(`${hubUrl}/api/notifications?scope=${scope}`, { method: 'DELETE' }).catch(() => {});
    } catch (e) {
      console.log('Error clearing notifications:', e);
    }
  };

  // Setup Android notification channel, request permissions, and register push token
  useEffect(() => {
    const setupNotifications = async () => {
      try {
        if (Platform.OS === 'android') {
          await Notifications.setNotificationChannelAsync('default', {
            name: 'Antigravity Hub Alerts',
            importance: Notifications.AndroidImportance.MAX,
            vibrationPattern: [0, 250, 250, 250],
            lightColor: '#6366f1',
            sound: 'default',
            enableVibrate: true,
            showBadge: true,
          });
        }

        const { status: existingStatus } = await Notifications.getPermissionsAsync();
        let finalStatus = existingStatus;
        if (existingStatus !== 'granted') {
          const { status } = await Notifications.requestPermissionsAsync();
          finalStatus = status;
        }

        if (finalStatus === 'granted') {
          try {
            const tokenData = await Notifications.getExpoPushTokenAsync().catch(() => null);
            if (tokenData && tokenData.data) {
              pushTokenRef.current = tokenData.data;
              console.log('Registered Expo Push Token:', tokenData.data);
              fetch(`${hubUrl}/api/devices/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  device_id: 'android_' + (Platform.OS || 'mobile'),
                  device_name: 'Android Mobile',
                  push_token: tokenData.data,
                  platform: Platform.OS || 'android',
                }),
              }).catch(() => {});
            }
          } catch (tErr) {
            console.log('Push token retrieval note (normal in development/offline):', tErr.message);
          }
        }
      } catch (err) {
        console.log('Error configuring notifications:', err);
      }
    };

    setupNotifications();
  }, [hubUrl]);

  // Fetch past notifications & register device
  const fetchNotifications = async (targetUrl = hubUrl) => {
    try {
      setLoading(true);
      const res = await fetch(`${targetUrl}/api/notifications?limit=50`);
      if (res.ok) {
        const data = await res.json();
        let filtered = data;
        if (autoClearMinutes && autoClearMinutes > 0) {
          const cutoff = Date.now() - autoClearMinutes * 60 * 1000;
          filtered = data.filter((n) => {
            const isCritical =
              n.level === 'critical' ||
              n.level === 'error' ||
              (n.action_id && (n.action_status === 'pending' || n.action?.status === 'pending'));
            if (isCritical) return true;
            if (!n.created_at) return true;
            const cleanDateStr = n.created_at.replace(' ', 'T') + (n.created_at.includes('Z') ? '' : 'Z');
            const ts = new Date(cleanDateStr).getTime();
            if (isNaN(ts)) return true;
            return ts > cutoff;
          });
          // Also trigger backend cleanup
          fetch(`${targetUrl}/api/notifications?older_than_minutes=${autoClearMinutes}&scope=non_critical`, {
            method: 'DELETE',
          }).catch(() => {});
        }
        setNotifications(filtered);
        setConnected(true);
        setConnectionStatus('connected');
        setConnectionError(null);

        // Ping register device with active push token if available
        fetch(`${targetUrl}/api/devices/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            device_id: 'android_' + (Platform.OS || 'mobile'),
            device_name: 'Android Mobile',
            push_token: pushTokenRef.current || '',
            platform: Platform.OS || 'android',
          }),
        }).catch(() => {});
      } else {
        setConnectionError(`HTTP ${res.status}`);
        if (!connected) setConnectionStatus('error');
      }
    } catch (err) {
      console.log('Error fetching notifications from', targetUrl, err.message);
      setConnectionError(err.message || 'Cannot reach PC');
      if (!connected) setConnectionStatus('error');
    } finally {
      setLoading(false);
    }
  };

  // AppState refresh and background polling interval
  useEffect(() => {
    const sub = AppState.addEventListener('change', (nextAppState) => {
      if (nextAppState === 'active') {
        fetchNotifications(hubUrl);
      }
    });

    const pollInterval = setInterval(() => {
      fetchNotifications(hubUrl);
    }, 12000);

    return () => {
      sub.remove();
      clearInterval(pollInterval);
    };
  }, [hubUrl]);

  // Connect WebSocket with auto-reconnect
  useEffect(() => {
    fetchNotifications(hubUrl);

    let socket;
    let isMounted = true;

    const connectWebSocket = () => {
      if (!isMounted) return;

      const wsUrl = hubUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/notifications';
      console.log('Connecting to WebSocket:', wsUrl);

      try {
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isMounted) return;
          setConnected(true);
          setConnectionStatus('connected');
          setConnectionError(null);
          console.log('Connected to Antigravity Hub at', hubUrl);
        };

        socket.onmessage = async (event) => {
          if (!isMounted) return;
          try {
            const payload = JSON.parse(event.data);
            if (Platform.OS !== 'web') {
              Vibration.vibrate(payload.level === 'critical' ? [0, 250, 100, 250] : 100);
            }
            setNotifications((prev) => [payload, ...prev]);

            // Trigger native Android system notification banner with sound & vibration
            try {
              await Notifications.scheduleNotificationAsync({
                content: {
                  title: payload.title || 'Antigravity Hub',
                  body: payload.message || '',
                  sound: 'default',
                  priority: Notifications.AndroidNotificationPriority.MAX,
                  data: payload,
                },
                trigger: null,
              });
            } catch (notifErr) {
              console.log('Error showing system notification banner:', notifErr);
            }
          } catch (e) {
            console.log('WS message parse error:', e);
          }
        };

        socket.onclose = () => {
          if (!isMounted) return;
          // Reconnect after 3 seconds
          retryTimeoutRef.current = setTimeout(connectWebSocket, 3000);
        };

        socket.onerror = (e) => {
          if (!isMounted) return;
          console.log('WebSocket error for', wsUrl);
        };
      } catch (err) {
        console.log('WS init error:', err);
      }
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      if (socket) socket.close();
    };
  }, [hubUrl]);

  // Handle responding to an OTP or action from mobile
  const handleActionSubmit = async (actionId, value) => {
    if (!value || !value.trim()) {
      Alert.alert('Required', 'Please enter a value or code.');
      return;
    }

    setSubmittingAction((prev) => ({ ...prev, [actionId]: true }));
    try {
      const res = await fetch(`${hubUrl}/api/actions/${actionId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, response_value: value.trim() }),
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
        Alert.alert('Delivered', 'Response sent to Antigravity CLI workflow.');
      } else {
        Alert.alert('Error', 'Could not send action to workflow.');
      }
    } catch (err) {
      Alert.alert('Connection Error', err.message);
    } finally {
      setSubmittingAction((prev) => ({ ...prev, [actionId]: false }));
    }
  };

  // Test notification helper
  const sendTestNotification = async () => {
    try {
      await fetch(`${hubUrl}/api/notify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow: 'auto_job_apply',
          title: '🎯 Test Application Alert',
          message: 'Applied to Senior AI Engineer at Zomato (Score: 92%). Tailored resume uploaded.',
          level: 'success',
          category: 'job_applied',
          metadata: { company: 'Zomato', role: 'Senior AI Engineer' },
        }),
      });
    } catch (e) {
      Alert.alert('Hub Offline', `Cannot reach ${hubUrl}. Check IP settings.`);
    }
  };

  // Category counts
  const jobCount = notifications.filter((n) => (n.workflow || '').toLowerCase().includes('job')).length;
  const actionCount = notifications.filter((n) => {
    const act = n.action_id || (n.action && n.action.action_id);
    const pending = n.action_status === 'pending' || (n.action && n.action.status === 'pending');
    return Boolean(act && pending);
  }).length;
  const errorCount = notifications.filter((n) => ['error', 'critical'].includes((n.level || '').toLowerCase())).length;

  // Filtered notifications
  const filteredNotifications = notifications.filter((item) => {
    const wf = (item.workflow || '').toLowerCase();
    const act = item.action_id || (item.action && item.action.action_id);
    const lvl = (item.level || '').toLowerCase();

    if (activeTab === 'JOB_APPLY') return wf.includes('job');
    if (activeTab === 'ACTIONS') return Boolean(act && (item.action_status === 'pending' || (item.action && item.action.status === 'pending')));
    if (activeTab === 'ERRORS') return lvl === 'error' || lvl === 'critical';
    return true;
  });

  const getLevelColor = (level) => {
    switch ((level || '').toLowerCase()) {
      case 'success':
        return '#10b981'; // Green
      case 'warning':
        return '#f59e0b'; // Amber
      case 'error':
        return '#ef4444'; // Red
      case 'critical':
        return '#ec4899'; // Pink
      default:
        return '#3b82f6'; // Blue
    }
  };

  const renderItem = ({ item }) => {
    const levelColor = getLevelColor(item.level);
    const actionId = item.action_id || (item.action && item.action.action_id);
    const actionType = item.action_type || (item.action && item.action.action_type);
    const actionPrompt = item.action_prompt || (item.action && item.action.prompt);
    const actionStatus = item.action_status || (item.action && item.action.status) || 'none';
    const actionResponse = item.action_response || (item.action && item.action.response_value);
    const isPending = actionStatus === 'pending';

    return (
      <View style={[styles.card, { borderLeftColor: levelColor, borderLeftWidth: 4 }]}>
        <View style={styles.cardHeader}>
          <View style={styles.badgeRow}>
            <View style={[styles.pill, { backgroundColor: '#1e293b' }]}>
              <Text style={styles.pillText}>{(item.workflow || 'GENERAL').toUpperCase()}</Text>
            </View>
            <View style={[styles.pill, { backgroundColor: levelColor + '25' }]}>
              <Text style={[styles.pillText, { color: levelColor }]}>
                {(item.level || 'INFO').toUpperCase()}
              </Text>
            </View>
          </View>
          <View style={styles.cardHeaderRight}>
            <Text style={styles.timeText}>{formatNotificationTime(item.created_at)}</Text>
            <TouchableOpacity
              onPress={() => dismissNotification(item.id)}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              style={styles.cardDismissBtn}
            >
              <Text style={styles.cardDismissText}>✕</Text>
            </TouchableOpacity>
          </View>
        </View>

        <Text style={styles.cardTitle}>{item.title}</Text>
        <Text style={styles.cardMessage}>{item.message}</Text>

        {item.screenshot_url ? (
          <TouchableOpacity onPress={() => setSelectedImage(item.screenshot_url)} style={styles.imageContainer}>
            <Image source={{ uri: item.screenshot_url }} style={styles.thumbnail} resizeMode="cover" />
            <View style={styles.imageOverlay}>
              <Text style={styles.imageOverlayText}>🔍 Tap to View Screenshot</Text>
            </View>
          </TouchableOpacity>
        ) : null}

        {actionId && isPending ? (
          <View style={styles.actionBox}>
            <Text style={styles.actionPromptText}>⚠️ {actionPrompt || 'Action Required:'}</Text>

            {actionType === 'input' ? (
              <View style={styles.inputRow}>
                <TextInput
                  style={styles.textInput}
                  placeholder="Enter code (e.g. OTP)..."
                  placeholderTextColor="#64748b"
                  value={actionInputs[actionId] || ''}
                  onChangeText={(val) => setActionInputs((prev) => ({ ...prev, [actionId]: val }))}
                  keyboardType="numeric"
                  autoFocus={true}
                />
                <TouchableOpacity
                  style={[styles.actionBtn, { backgroundColor: '#3b82f6' }]}
                  disabled={submittingAction[actionId]}
                  onPress={() => handleActionSubmit(actionId, actionInputs[actionId])}
                >
                  {submittingAction[actionId] ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.actionBtnText}>Send to CLI</Text>
                  )}
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.btnRow}>
                <TouchableOpacity
                  style={[styles.choiceBtn, { backgroundColor: '#10b981' }]}
                  onPress={() => handleActionSubmit(actionId, 'APPROVE')}
                >
                  <Text style={styles.actionBtnText}>✓ Approve & Submit</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.choiceBtn, { backgroundColor: '#475569' }]}
                  onPress={() => handleActionSubmit(actionId, 'SKIP')}
                >
                  <Text style={styles.actionBtnText}>✕ Skip</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        ) : null}

        {actionId && !isPending && actionResponse ? (
          <View style={styles.resolvedBox}>
            <Text style={styles.resolvedText}>✓ Responded from mobile: "{actionResponse}"</Text>
          </View>
        ) : null}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

      {/* App Bar */}
      <View style={styles.appBar}>
        <View style={styles.titleBrand}>
          <Image source={require('./assets/logo.png')} style={styles.appLogo} />
          <TouchableOpacity onPress={() => fetchNotifications(hubUrl)} style={styles.statusPill}>
            <View style={[styles.statusDot, { backgroundColor: connected ? '#10b981' : '#ef4444' }]} />
            <Text style={styles.statusText}>{connected ? 'Online' : 'Offline'}</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.headerBtnRow}>
          <TouchableOpacity onPress={sendTestNotification} style={styles.iconBtn}>
            <Text style={styles.iconBtnText}>🔔 Test</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setCleanupModalVisible(true)} style={styles.iconBtn}>
            <Text style={styles.iconBtnText}>🧹 Clear</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => {
              setTempIp(hubUrl);
              setIpModalVisible(true);
            }}
            style={styles.iconBtn}
          >
            <Text style={styles.iconBtnText}>⚙️ IP</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => fetchNotifications(hubUrl)} style={styles.iconBtn}>
            <Text style={styles.iconBtnText}>🔄</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Tabs */}
      <View style={styles.tabContainer}>
        {[
          { key: 'ALL', label: 'All', count: notifications.length },
          { key: 'JOB_APPLY', label: 'Jobs', count: jobCount },
          { key: 'ACTIONS', label: 'Actions', count: actionCount },
          { key: 'ERRORS', label: 'Errors', count: errorCount },
        ].map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <TouchableOpacity
              key={tab.key}
              style={[styles.tabBtn, isActive && styles.tabBtnActive]}
              onPress={() => setActiveTab(tab.key)}
            >
              <View style={styles.tabContentRow}>
                <Text style={[styles.tabText, isActive && styles.tabTextActive]}>
                  {tab.label}
                </Text>
                {tab.count > 0 ? (
                  <View style={[styles.tabBadge, isActive ? styles.tabBadgeActive : styles.tabBadgeInactive]}>
                    <Text style={[styles.tabBadgeText, isActive ? styles.tabBadgeTextActive : styles.tabBadgeTextInactive]}>
                      {tab.count}
                    </Text>
                  </View>
                ) : null}
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Notifications List */}
      <FlatList
        data={filteredNotifications}
        keyExtractor={(item, index) => item.id || String(index)}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        refreshing={loading}
        onRefresh={() => fetchNotifications(hubUrl)}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            {connected ? (
              <>
                <Text style={styles.emptyTitle}>No Notifications Yet</Text>
                <Text style={styles.emptySubtitle}>
                  Connected live to {hubUrl}. Run auto_job_apply on your PC or tap [🔔 Test] to trigger an alert.
                </Text>
              </>
            ) : (
              <>
                <Text style={[styles.emptyTitle, { color: '#ef4444' }]}>⚠️ PC Hub Not Connected</Text>
                <Text style={styles.emptySubtitle}>
                  Attempting to reach: {hubUrl}{'\n'}
                  {connectionError ? `Error: ${connectionError}\n\n` : '\n'}
                  1. Verify your phone & PC are on the same Wi-Fi.{'\n'}
                  2. Make sure backend is running on your PC.{'\n'}
                  3. If your PC IP changed, tap [⚙️ IP] above.
                </Text>
                <TouchableOpacity
                  style={[styles.modalBtn, { backgroundColor: '#3b82f6', marginTop: 15 }]}
                  onPress={() => fetchNotifications(hubUrl)}
                >
                  <Text style={styles.modalBtnText}>🔄 Retry Connection</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        }
      />

      {/* IP Settings Modal */}
      <Modal visible={ipModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Local Hub Connection</Text>
            <Text style={styles.modalDesc}>
              Enter your computer's IP address on Wi-Fi (e.g. 192.168.31.210):
            </Text>
            <TextInput
              style={styles.modalInput}
              value={tempIp}
              onChangeText={setTempIp}
              placeholder="http://192.168.31.210:8765"
              placeholderTextColor="#64748b"
              autoCapitalize="none"
              autoCorrect={false}
            />

            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>Quick Presets:</Text>
              <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
                <TouchableOpacity
                  style={{ backgroundColor: '#1e293b', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, borderWidth: 1, borderColor: '#334155' }}
                  onPress={() => setTempIp('http://192.168.31.210:8765')}
                >
                  <Text style={{ color: '#38bdf8', fontSize: 12 }}>PC Wi-Fi (192.168.31.210)</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={{ backgroundColor: '#1e293b', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, borderWidth: 1, borderColor: '#334155' }}
                  onPress={() => setTempIp('http://10.0.2.2:8765')}
                >
                  <Text style={{ color: '#94a3b8', fontSize: 12 }}>Emulator (10.0.2.2)</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.modalBtnRow}>
              <TouchableOpacity
                style={[styles.modalBtn, { backgroundColor: '#334155' }]}
                onPress={() => setIpModalVisible(false)}
              >
                <Text style={styles.modalBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalBtn, { backgroundColor: '#3b82f6' }]}
                onPress={() => {
                  const cleaned = cleanHubUrl(tempIp);
                  setHubUrl(cleaned);
                  setTempIp(cleaned);
                  AsyncStorage.setItem('antigravity_hub_url', cleaned).catch(() => {});
                  setIpModalVisible(false);
                  setConnected(false);
                  setConnectionStatus('connecting');
                  setConnectionError(null);
                  fetchNotifications(cleaned);
                }}
              >
                <Text style={styles.modalBtnText}>Save & Connect</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Cleanup Options Modal */}
      <Modal visible={cleanupModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <Text style={styles.modalTitle}>Notification Cleanup</Text>
              <TouchableOpacity onPress={() => setCleanupModalVisible(false)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                <Text style={{ color: '#94a3b8', fontSize: 16, fontWeight: 'bold' }}>✕</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.modalDesc}>
              Clear notifications from this device or configure auto-cleanup:
            </Text>

            {/* Clear Action Buttons */}
            <View style={{ gap: 10, marginBottom: 18 }}>
              <TouchableOpacity
                style={[styles.cleanupBtn, { backgroundColor: '#1e293b', borderColor: '#3b82f6' }]}
                onPress={() => handleClearNotifications('non_critical')}
              >
                <Text style={[styles.cleanupBtnTitle, { color: '#38bdf8' }]}>🧹 Clear Routine Alerts</Text>
                <Text style={styles.cleanupBtnSub}>Deletes info and applied job cards. Preserves pending actions & errors.</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.cleanupBtn, { backgroundColor: '#1e293b', borderColor: '#ef4444' }]}
                onPress={() => {
                  Alert.alert(
                    'Clear All',
                    'Are you sure you want to delete all notifications?',
                    [
                      { text: 'Cancel', style: 'cancel' },
                      { text: 'Clear All', style: 'destructive', onPress: () => handleClearNotifications('all') },
                    ]
                  );
                }}
              >
                <Text style={[styles.cleanupBtnTitle, { color: '#f87171' }]}>🗑️ Clear All Notifications</Text>
                <Text style={styles.cleanupBtnSub}>Deletes all notification history from phone and database.</Text>
              </TouchableOpacity>
            </View>

            {/* Auto-Clear Configuration */}
            <View style={{ borderTopWidth: 1, borderTopColor: '#1e293b', paddingTop: 14, marginBottom: 16 }}>
              <Text style={{ fontSize: 13, fontWeight: '700', color: '#f8fafc', marginBottom: 4 }}>
                ⏱️ Auto-Clear Routine Alerts:
              </Text>
              <Text style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>
                Automatically prune non-critical alerts older than:
              </Text>

              <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap' }}>
                {[
                  { label: 'Off', mins: 0 },
                  { label: '5m', mins: 5 },
                  { label: '15m (Rec)', mins: 15 },
                  { label: '1h', mins: 60 },
                  { label: '24h', mins: 1440 },
                ].map((opt) => {
                  const isSelected = autoClearMinutes === opt.mins;
                  return (
                    <TouchableOpacity
                      key={opt.mins}
                      style={[
                        styles.presetChip,
                        isSelected && { backgroundColor: '#2563eb', borderColor: '#3b82f6' },
                      ]}
                      onPress={() => updateAutoClearMinutes(opt.mins)}
                    >
                      <Text
                        style={[
                          styles.presetChipText,
                          isSelected && { color: '#ffffff', fontWeight: 'bold' },
                        ]}
                      >
                        {opt.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>

            <TouchableOpacity
              style={[styles.modalBtn, { backgroundColor: '#334155', alignSelf: 'stretch', alignItems: 'center' }]}
              onPress={() => setCleanupModalVisible(false)}
            >
              <Text style={styles.modalBtnText}>Done</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Fullscreen Screenshot Modal */}
      <Modal visible={Boolean(selectedImage)} transparent animationType="fade">
        <View style={styles.imageModalOverlay}>
          <TouchableOpacity style={styles.closeImageBtn} onPress={() => setSelectedImage(null)}>
            <Text style={styles.closeImageText}>✕ Close</Text>
          </TouchableOpacity>
          {selectedImage ? (
            <Image source={{ uri: selectedImage }} style={styles.fullImage} resizeMode="contain" />
          ) : null}
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#090d16',
  },
  appBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 10,
    backgroundColor: '#0f172a',
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
  },
  titleBrand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  appLogo: {
    width: 32,
    height: 32,
    borderRadius: 8,
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    marginRight: 5,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#cbd5e1',
  },
  headerBtnRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  iconBtn: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  iconBtnText: {
    color: '#f1f5f9',
    fontSize: 11,
    fontWeight: '700',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#0f172a',
    paddingHorizontal: 12,
    paddingTop: 6,
    paddingBottom: 8,
    gap: 6,
  },
  tabBtn: {
    flex: 1,
    height: 34,
    borderRadius: 8,
    backgroundColor: '#1e293b',
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabBtnActive: {
    backgroundColor: '#2563eb',
  },
  tabContentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  tabText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#94a3b8',
  },
  tabTextActive: {
    color: '#ffffff',
  },
  tabBadge: {
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 10,
  },
  tabBadgeActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
  },
  tabBadgeInactive: {
    backgroundColor: '#334155',
  },
  tabBadgeText: {
    fontSize: 9,
    fontWeight: '700',
  },
  tabBadgeTextActive: {
    color: '#ffffff',
  },
  tabBadgeTextInactive: {
    color: '#cbd5e1',
  },
  cardHeaderRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardDismissBtn: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: '#1e293b',
  },
  cardDismissText: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: 'bold',
  },
  cleanupBtn: {
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
  },
  cleanupBtnTitle: {
    fontSize: 13,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  cleanupBtnSub: {
    fontSize: 11,
    color: '#94a3b8',
    lineHeight: 15,
  },
  presetChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 8,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
  },
  presetChipText: {
    color: '#94a3b8',
    fontSize: 12,
  },
  listContent: {
    padding: 14,
  },
  card: {
    backgroundColor: '#0f172a',
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#1e293b',
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 6,
  },
  pill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  pillText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#cbd5e1',
  },
  timeText: {
    fontSize: 11,
    color: '#64748b',
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#f8fafc',
    marginBottom: 4,
  },
  cardMessage: {
    fontSize: 13,
    color: '#94a3b8',
    lineHeight: 18,
  },
  imageContainer: {
    marginTop: 10,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
    borderWidth: 1,
    borderColor: '#334155',
  },
  thumbnail: {
    width: '100%',
    height: 140,
    backgroundColor: '#020617',
  },
  imageOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    paddingVertical: 5,
    alignItems: 'center',
  },
  imageOverlayText: {
    color: '#38bdf8',
    fontSize: 11,
    fontWeight: '600',
  },
  actionBox: {
    marginTop: 12,
    padding: 10,
    backgroundColor: '#1e1b4b',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#4338ca',
  },
  actionPromptText: {
    color: '#facc15',
    fontWeight: '700',
    fontSize: 12,
    marginBottom: 8,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
  },
  textInput: {
    flex: 1,
    backgroundColor: '#0f172a',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#f8fafc',
    borderWidth: 1,
    borderColor: '#6366f1',
    fontSize: 14,
  },
  actionBtn: {
    paddingHorizontal: 14,
    justifyContent: 'center',
    borderRadius: 8,
  },
  actionBtnText: {
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  btnRow: {
    flexDirection: 'row',
    gap: 10,
  },
  choiceBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  resolvedBox: {
    marginTop: 10,
    padding: 6,
    backgroundColor: '#064e3b',
    borderRadius: 6,
  },
  resolvedText: {
    color: '#6ee7b7',
    fontSize: 11,
    fontWeight: '600',
  },
  emptyContainer: {
    marginTop: 80,
    alignItems: 'center',
    paddingHorizontal: 30,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#475569',
    marginBottom: 6,
  },
  emptySubtitle: {
    fontSize: 13,
    color: '#334155',
    textAlign: 'center',
    lineHeight: 18,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    padding: 24,
  },
  modalContent: {
    backgroundColor: '#0f172a',
    borderRadius: 14,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#f8fafc',
    marginBottom: 8,
  },
  modalDesc: {
    fontSize: 13,
    color: '#94a3b8',
    marginBottom: 14,
    lineHeight: 18,
  },
  modalInput: {
    backgroundColor: '#1e293b',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: '#f8fafc',
    fontSize: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#475569',
  },
  modalBtnRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 10,
  },
  modalBtn: {
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 8,
  },
  modalBtnText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 13,
  },
  imageModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.92)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeImageBtn: {
    position: 'absolute',
    top: 50,
    right: 20,
    zIndex: 10,
    backgroundColor: '#334155',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  closeImageText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  fullImage: {
    width: '94%',
    height: '80%',
  },
});
