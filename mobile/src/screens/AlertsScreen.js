import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Image,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { NeoColors } from '../theme/neomorphism';
import NeoCard from '../components/NeoCard';
import NeoPill from '../components/NeoPill';

export default function AlertsScreen({
  notifications,
  hubUrl,
  hubToken,
  loading,
  onRefresh,
  onDismiss,
  onSubmitAction,
  onOpenScreenshot,
  onClearNotifications,
}) {
  const [activeTab, setActiveTab] = useState('ALL'); // ALL, JOBS, ACTIONS, ERRORS
  const [actionInputs, setActionInputs] = useState({});
  const [submittingAction, setSubmittingAction] = useState({});
  const [expandedCards, setExpandedCards] = useState({});

  const toggleExpand = (id) => {
    setExpandedCards((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const resolveScreenshotUrl = (rawUrl) => {
    if (!rawUrl) return null;
    let u = String(rawUrl).trim();
    if (!u) return null;

    // Check if it points to a screenshot path
    const screenshotMatch = u.match(/(\/(?:api\/)?screenshots\/[^\s?#]+)/);
    const base = (hubUrl || '').replace(/\/+$/, '');

    let finalUrl = u;
    if (screenshotMatch && base) {
      // Re-base directly onto the active hubUrl that the phone is actively connected to
      const path = screenshotMatch[1].startsWith('/api/')
        ? screenshotMatch[1]
        : `/api${screenshotMatch[1]}`;
      finalUrl = `${base}${path}`;
    } else if (base) {
      finalUrl = finalUrl.replace(/http:\/\/(localhost|127\.0\.0\.1)(:\d+)?/, base);
      if (finalUrl.startsWith('/')) {
        finalUrl = `${base}${finalUrl}`;
      }
    }

    // Preserve existing token in rawUrl or append active hubToken
    const rawTokenMatch = u.match(/[?&]token=([^&]+)/);
    const token = (rawTokenMatch && rawTokenMatch[1]) || hubToken || '';
    if (token && !finalUrl.includes('token=')) {
      finalUrl += (finalUrl.includes('?') ? '&' : '?') + `token=${encodeURIComponent(token)}`;
    }
    return finalUrl;
  };

  const handleAction = async (actionId, value) => {
    setSubmittingAction((prev) => ({ ...prev, [actionId]: true }));
    try {
      await onSubmitAction(actionId, value);
    } finally {
      setSubmittingAction((prev) => ({ ...prev, [actionId]: false }));
    }
  };

  const handlePickAndUploadScreenshots = async (actionId) => {
    setSubmittingAction((prev) => ({ ...prev, [actionId]: true }));
    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('Permission Denied', 'Please grant access to your photo gallery to attach screenshots.');
        return;
      }

      const pickerResult = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsMultipleSelection: true,
        quality: 0.85,
        base64: true,
      });

      if (pickerResult.canceled || !pickerResult.assets || pickerResult.assets.length === 0) {
        return;
      }

      const imagesBase64 = pickerResult.assets
        .map((a) => (a.base64 ? `data:image/png;base64,${a.base64}` : null))
        .filter(Boolean);

      if (imagesBase64.length === 0) {
        Alert.alert('Error', 'Could not read image content from gallery.');
        return;
      }

      const base = (hubUrl || '').replace(/\/+$/, '');
      const uploadRes = await fetch(`${base}/api/screenshots/upload`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(hubToken ? { 'X-Hub-Token': hubToken, 'Authorization': `Bearer ${hubToken}` } : {}),
        },
        body: JSON.stringify({ images: imagesBase64 }),
      });

      if (!uploadRes.ok) {
        throw new Error(`Upload failed with status ${uploadRes.status}`);
      }

      const uploadData = await uploadRes.json();
      const paths = uploadData.screenshot_paths || [];
      if (paths.length === 0) {
        throw new Error('No saved screenshot paths returned by relay');
      }

      // Deliver uploaded paths to the waiting workflow
      await onSubmitAction(actionId, JSON.stringify(paths));
      Alert.alert('Success', `Attached and uploaded ${paths.length} screenshot(s)!`);
    } catch (err) {
      console.log('Image picker / upload error:', err);
      Alert.alert('Upload Error', err.message || 'Could not upload screenshots to relay.');
    } finally {
      setSubmittingAction((prev) => ({ ...prev, [actionId]: false }));
    }
  };

  const getLevelColor = (level) => {
    switch ((level || '').toLowerCase()) {
      case 'success':
        return '#059669';
      case 'warning':
        return '#d97706';
      case 'error':
        return '#dc2626';
      case 'critical':
        return '#e11d48';
      default:
        return '#2563eb';
    }
  };

  const jobCount = notifications.filter((n) => (n.workflow || '').toLowerCase().includes('job')).length;
  const actionCount = notifications.filter((n) => {
    const act = n.action_id || (n.action && n.action.action_id);
    const pending = n.action_status === 'pending' || (n.action && n.action.status === 'pending');
    return Boolean(act && pending);
  }).length;
  const errorCount = notifications.filter((n) => ['error', 'critical'].includes((n.level || '').toLowerCase())).length;

  const filtered = notifications.filter((item) => {
    const wf = (item.workflow || '').toLowerCase();
    const act = item.action_id || (item.action && item.action.action_id);
    const lvl = (item.level || '').toLowerCase();

    if (activeTab === 'JOBS') return wf.includes('job');
    if (activeTab === 'ACTIONS') return Boolean(act && (item.action_status === 'pending' || (item.action && item.action.status === 'pending')));
    if (activeTab === 'ERRORS') return lvl === 'error' || lvl === 'critical';
    return true;
  });

  const renderItem = ({ item }) => {
    const levelColor = getLevelColor(item.level);
    const actionId = item.action_id || (item.action && item.action.action_id);
    const actionType = item.action_type || (item.action && item.action.action_type);
    const actionPrompt = item.action_prompt || (item.action && item.action.prompt);
    const actionStatus = item.action_status || (item.action && item.action.status) || 'none';
    const actionResponse = item.action_response || (item.action && item.action.response_value);

    let rawOptions =
      (item.action && item.action.options) ||
      item.action_options ||
      item.options ||
      [];
    if (typeof rawOptions === 'string') {
      try {
        rawOptions = JSON.parse(rawOptions);
      } catch (e) {
        rawOptions = [rawOptions];
      }
    }
    const actionOptions =
      Array.isArray(rawOptions) && rawOptions.length > 0
        ? rawOptions
        : ['Approve & Publish', 'Recreate Draft', 'Cancel'];

    const isPending = actionStatus === 'pending';
    const resolvedScreenshot = resolveScreenshotUrl(item.screenshot_url);

    let metaObj = item.metadata;
    if (!metaObj && item.metadata_json) {
      try {
        metaObj = JSON.parse(item.metadata_json);
      } catch (e) {}
    }

    let allScreenshotUrls = [];
    if (metaObj && Array.isArray(metaObj.screenshot_urls) && metaObj.screenshot_urls.length > 0) {
      allScreenshotUrls = metaObj.screenshot_urls.map(resolveScreenshotUrl).filter(Boolean);
    } else if (resolvedScreenshot) {
      allScreenshotUrls = [resolvedScreenshot];
    }
    const fullDraft = (metaObj && metaObj.post_content) || item.message || '';
    const hasLongContent = fullDraft.length > 100 || fullDraft.includes('\n');
    const isExpanded = Boolean(expandedCards[item.id]);

    return (
      <NeoCard style={[styles.card, { borderLeftColor: levelColor, borderLeftWidth: 4 }]}>
        <View style={styles.cardHeader}>
          <View style={styles.badgeRow}>
            <NeoPill
              label={(item.workflow || 'GENERAL').toUpperCase()}
              color="#334155"
              bgColor="#e2e8f0"
            />
            <NeoPill
              label={(item.level || 'INFO').toUpperCase()}
              color={levelColor}
            />
          </View>

          <TouchableOpacity
            onPress={() => onDismiss(item.id)}
            style={styles.dismissBtn}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Text style={styles.dismissText}>✕</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.cardTitle}>{item.title}</Text>

        {/* Content / Full Post Draft Preview */}
        {hasLongContent ? (
          <View style={styles.contentBox}>
            <View style={styles.contentHeader}>
              <Text style={styles.contentHeaderTitle}>
                {item.category === 'linkedin_post' || (item.workflow || '').toLowerCase().includes('job')
                  ? '📝 Post Draft Preview:'
                  : '📋 Full Details:'}
              </Text>
              <Text style={styles.charCountText}>
                {fullDraft.length} chars
              </Text>
            </View>

            <Text
              style={styles.contentText}
              numberOfLines={isExpanded ? undefined : 6}
              selectable={true}
            >
              {fullDraft}
            </Text>

            <TouchableOpacity
              onPress={() => toggleExpand(item.id)}
              style={styles.expandBarBtn}
              activeOpacity={0.7}
            >
              <Text style={styles.expandBarBtnText}>
                {isExpanded ? '▲ Collapse Draft' : '▼ Read Full Post & Details'}
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <Text style={styles.cardMessage} selectable={true}>{item.message}</Text>
        )}

        {/* Screenshot View(s) & Modal Opener */}
        {allScreenshotUrls.length > 1 ? (
          <View style={styles.multiScreenshotsBox}>
            <View style={styles.multiScreenshotsHeader}>
              <Text style={styles.multiScreenshotsTitle}>
                📸 {allScreenshotUrls.length} Screenshots Attached:
              </Text>
              <Text style={styles.multiScreenshotsHint}>Swipe ➔</Text>
            </View>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.carouselScroll}
              contentContainerStyle={{ paddingRight: 10 }}
            >
              {allScreenshotUrls.map((url, idx) => (
                <TouchableOpacity
                  key={idx}
                  onPress={() => onOpenScreenshot(allScreenshotUrls)}
                  style={styles.carouselItem}
                  activeOpacity={0.85}
                >
                  <Image
                    source={{ uri: url }}
                    style={styles.carouselThumbnail}
                    resizeMode="cover"
                  />
                  <View style={styles.carouselBadge}>
                    <Text style={styles.carouselBadgeText}>#{idx + 1}</Text>
                  </View>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        ) : allScreenshotUrls.length === 1 ? (
          <TouchableOpacity
            onPress={() => onOpenScreenshot(allScreenshotUrls[0])}
            style={styles.imageBox}
            activeOpacity={0.85}
          >
            <Image
              source={{ uri: allScreenshotUrls[0] }}
              style={styles.thumbnail}
              resizeMode="cover"
            />
            <View style={styles.imageOverlay}>
              <Text style={styles.imageOverlayText}>🔍 Tap to View Fullscreen Screenshot</Text>
            </View>
          </TouchableOpacity>
        ) : null}

        {/* Action Required Box */}
        {actionId && isPending ? (
          <View style={styles.actionBox}>
            <Text style={styles.actionPromptText}>⚠️ {actionPrompt || 'Action Required:'}</Text>

            {actionType === 'screenshot_upload' ? (
              <View style={styles.screenshotActionCol}>
                <TouchableOpacity
                  style={[styles.choiceBtn, { backgroundColor: '#4f46e5', paddingVertical: 12, marginBottom: 8 }]}
                  disabled={submittingAction[actionId]}
                  onPress={() => handlePickAndUploadScreenshots(actionId)}
                >
                  {submittingAction[actionId] ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.choiceBtnText}>🖼️ Pick Photos from Phone Gallery</Text>
                  )}
                </TouchableOpacity>

                <View style={styles.inputRow}>
                  <TextInput
                    style={styles.actionInput}
                    placeholder="Or enter path / URL..."
                    placeholderTextColor="#94a3b8"
                    value={actionInputs[actionId] || ''}
                    onChangeText={(val) => setActionInputs((prev) => ({ ...prev, [actionId]: val }))}
                  />
                  <TouchableOpacity
                    style={[styles.choiceBtn, { backgroundColor: '#0284c7', minWidth: 65 }]}
                    disabled={submittingAction[actionId]}
                    onPress={() => handleAction(actionId, actionInputs[actionId] || 'SKIP')}
                  >
                    <Text style={styles.choiceBtnText}>Submit</Text>
                  </TouchableOpacity>
                </View>

                <TouchableOpacity
                  style={styles.skipBtn}
                  disabled={submittingAction[actionId]}
                  onPress={() => handleAction(actionId, 'SKIP')}
                >
                  <Text style={styles.skipBtnText}>⏩ Skip Screenshots (Post Text-Only)</Text>
                </TouchableOpacity>
              </View>
            ) : actionType === 'input' ? (
              <View style={styles.inputRow}>
                <TextInput
                  style={styles.actionInput}
                  placeholder="Enter code or response..."
                  placeholderTextColor="#94a3b8"
                  value={actionInputs[actionId] || ''}
                  onChangeText={(val) => setActionInputs((prev) => ({ ...prev, [actionId]: val }))}
                />
                <TouchableOpacity
                  style={styles.actionSubmitBtn}
                  disabled={submittingAction[actionId]}
                  onPress={() => handleAction(actionId, actionInputs[actionId])}
                >
                  {submittingAction[actionId] ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <Text style={styles.actionSubmitText}>Send</Text>
                  )}
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.btnRow}>
                {actionOptions.map((opt, idx) => {
                  const optUpper = String(opt).toUpperCase();
                  const isApprove = optUpper.includes('APPROVE') || optUpper.includes('POST') || optUpper.includes('YES');
                  const isRecreate = optUpper.includes('RECREATE') || optUpper.includes('REGENERATE') || optUpper.includes('EDIT');
                  const isCancel = optUpper.includes('CANCEL') || optUpper.includes('SKIP') || optUpper.includes('REJECT');

                  let bgColor = '#475569';
                  let icon = '• ';
                  if (isApprove) {
                    bgColor = '#10b981';
                    icon = '✓ ';
                  } else if (isRecreate) {
                    bgColor = '#0284c7';
                    icon = '🔄 ';
                  } else if (isCancel) {
                    bgColor = '#ef4444';
                    icon = '✕ ';
                  }

                  return (
                    <TouchableOpacity
                      key={idx}
                      style={[styles.choiceBtn, { backgroundColor: bgColor, minWidth: 95, marginVertical: 3 }]}
                      disabled={submittingAction[actionId]}
                      onPress={() => handleAction(actionId, opt)}
                    >
                      <Text style={styles.choiceBtnText}>{icon}{opt}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            )}
          </View>
        ) : null}

        {actionId && !isPending && actionResponse ? (
          <View style={styles.resolvedBox}>
            <Text style={styles.resolvedText}>✓ Responded: "{actionResponse}"</Text>
          </View>
        ) : null}
      </NeoCard>
    );
  };

  return (
    <View style={styles.container}>
      {/* Tab Filter Pills */}
      <View style={styles.tabContainer}>
        {[
          { key: 'ALL', label: 'All', count: notifications.length },
          { key: 'JOBS', label: 'Jobs', count: jobCount },
          { key: 'ACTIONS', label: 'Actions', count: actionCount },
          { key: 'ERRORS', label: 'Errors', count: errorCount },
        ].map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <TouchableOpacity
              key={tab.key}
              onPress={() => setActiveTab(tab.key)}
              style={[styles.tabBtn, isActive && styles.tabBtnActive]}
            >
              <Text style={[styles.tabText, isActive && styles.tabTextActive]}>
                {tab.label}
              </Text>
              {tab.count > 0 ? (
                <View style={[styles.badge, isActive && styles.badgeActive]}>
                  <Text style={[styles.badgeText, isActive && styles.badgeTextActive]}>
                    {tab.count}
                  </Text>
                </View>
              ) : null}
            </TouchableOpacity>
          );
        })}
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        refreshing={loading}
        onRefresh={onRefresh}
        contentContainerStyle={styles.listContent}
        renderItem={renderItem}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyIcon}>🔔</Text>
            <Text style={styles.emptyTitle}>No Live Alerts</Text>
            <Text style={styles.emptyDesc}>
              Antigravity CLI workflows (auto job apply, OTP requests, screenshots) will appear here in real time.
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: NeoColors.background,
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 8,
  },
  tabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: '#ebf1f8',
    borderWidth: 1,
    borderColor: '#c5d2e3',
  },
  tabBtnActive: {
    backgroundColor: '#4f46e5',
    borderColor: '#4338ca',
  },
  tabText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#475569',
  },
  tabTextActive: {
    color: '#ffffff',
  },
  badge: {
    marginLeft: 4,
    backgroundColor: '#cbd5e1',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 8,
  },
  badgeActive: {
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
  badgeText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#1e293b',
  },
  badgeTextActive: {
    color: '#ffffff',
  },
  listContent: {
    padding: 14,
    paddingTop: 4,
  },
  card: {
    padding: 14,
    marginBottom: 12,
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
  dismissBtn: {
    padding: 4,
  },
  dismissText: {
    color: '#94a3b8',
    fontWeight: 'bold',
    fontSize: 14,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: NeoColors.textPrimary,
    marginBottom: 4,
  },
  cardMessage: {
    fontSize: 12,
    color: NeoColors.textSecondary,
    lineHeight: 17,
  },
  contentBox: {
    marginTop: 8,
    backgroundColor: '#f8fafc',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  contentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
    paddingBottom: 4,
  },
  contentHeaderTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#334155',
  },
  charCountText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#64748b',
    backgroundColor: '#e2e8f0',
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 4,
  },
  expandBarBtn: {
    marginTop: 8,
    paddingVertical: 5,
    paddingHorizontal: 8,
    backgroundColor: '#e0f2fe',
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#bae6fd',
  },
  expandBarBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#0284c7',
  },
  contentText: {
    fontSize: 12,
    color: '#1e293b',
    lineHeight: 18,
  },
  imageBox: {
    marginTop: 10,
    borderRadius: 10,
    overflow: 'hidden',
    position: 'relative',
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  thumbnail: {
    width: '100%',
    height: 140,
    backgroundColor: '#e2e8f0',
  },
  imageOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.75)',
    paddingVertical: 5,
    alignItems: 'center',
  },
  imageOverlayText: {
    color: '#38bdf8',
    fontSize: 11,
    fontWeight: '600',
  },
  actionBox: {
    marginTop: 10,
    padding: 10,
    backgroundColor: '#fffbeb',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#fde68a',
  },
  actionPromptText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#92400e',
    marginBottom: 8,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 8,
  },
  actionInput: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: '#d97706',
    fontSize: 14,
    color: '#1e293b',
  },
  actionSubmitBtn: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 14,
    justifyContent: 'center',
    borderRadius: 8,
  },
  actionSubmitText: {
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  btnRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  choiceBtn: {
    flexGrow: 1,
    paddingVertical: 9,
    paddingHorizontal: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.15,
    shadowRadius: 1.5,
  },
  choiceBtnText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 12,
  },
  resolvedBox: {
    marginTop: 8,
    padding: 6,
    backgroundColor: '#d1fae5',
    borderRadius: 6,
  },
  resolvedText: {
    color: '#065f46',
    fontSize: 11,
    fontWeight: '600',
  },
  emptyContainer: {
    padding: 30,
    alignItems: 'center',
    marginTop: 60,
    backgroundColor: '#ebf1f8',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#d5e0ee',
  },
  emptyIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: NeoColors.textPrimary,
    marginBottom: 4,
  },
  emptyDesc: {
    fontSize: 12,
    color: NeoColors.textSecondary,
    textAlign: 'center',
    lineHeight: 18,
  },
  multiScreenshotsBox: {
    marginTop: 10,
    backgroundColor: '#f1f5f9',
    borderRadius: 10,
    padding: 8,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  multiScreenshotsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
    paddingHorizontal: 2,
  },
  multiScreenshotsTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#334155',
  },
  multiScreenshotsHint: {
    fontSize: 10,
    fontWeight: '600',
    color: '#0284c7',
  },
  carouselScroll: {
    flexDirection: 'row',
  },
  carouselItem: {
    width: 175,
    height: 110,
    borderRadius: 8,
    overflow: 'hidden',
    marginRight: 8,
    position: 'relative',
    borderWidth: 1,
    borderColor: '#94a3b8',
    backgroundColor: '#e2e8f0',
  },
  carouselThumbnail: {
    width: '100%',
    height: '100%',
  },
  carouselBadge: {
    position: 'absolute',
    top: 5,
    right: 5,
    backgroundColor: 'rgba(15, 23, 42, 0.75)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  carouselBadgeText: {
    color: '#38bdf8',
    fontSize: 10,
    fontWeight: 'bold',
  },
  screenshotActionCol: {
    marginTop: 4,
  },
  skipBtn: {
    paddingVertical: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
    backgroundColor: '#f1f5f9',
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  skipBtnText: {
    fontSize: 11,
    color: '#64748b',
    fontWeight: '700',
  },
});
