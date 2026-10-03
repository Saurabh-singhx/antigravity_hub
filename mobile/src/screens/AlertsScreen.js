import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  Image,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { NeoColors } from '../theme/neomorphism';
import NeoCard from '../components/NeoCard';
import NeoPill from '../components/NeoPill';

export default function AlertsScreen({
  notifications,
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

  const handleAction = async (actionId, value) => {
    setSubmittingAction((prev) => ({ ...prev, [actionId]: true }));
    try {
      await onSubmitAction(actionId, value);
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
    const isPending = actionStatus === 'pending';

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
        <Text style={styles.cardMessage}>{item.message}</Text>

        {item.screenshot_url ? (
          <TouchableOpacity
            onPress={() => onOpenScreenshot(item.screenshot_url)}
            style={styles.imageBox}
          >
            <Image source={{ uri: item.screenshot_url }} style={styles.thumbnail} resizeMode="cover" />
            <View style={styles.imageOverlay}>
              <Text style={styles.imageOverlayText}>🔍 Tap to View Screenshot</Text>
            </View>
          </TouchableOpacity>
        ) : null}

        {/* Action Required Box */}
        {actionId && isPending ? (
          <View style={styles.actionBox}>
            <Text style={styles.actionPromptText}>⚠️ {actionPrompt || 'Action Required:'}</Text>

            {actionType === 'input' ? (
              <View style={styles.inputRow}>
                <TextInput
                  style={styles.actionInput}
                  placeholder="Enter code (e.g. OTP)..."
                  placeholderTextColor="#94a3b8"
                  value={actionInputs[actionId] || ''}
                  onChangeText={(val) => setActionInputs((prev) => ({ ...prev, [actionId]: val }))}
                  keyboardType="numeric"
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
                <TouchableOpacity
                  style={[styles.choiceBtn, { backgroundColor: '#10b981' }]}
                  onPress={() => handleAction(actionId, 'APPROVE')}
                >
                  <Text style={styles.choiceBtnText}>✓ Approve & Submit</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.choiceBtn, { backgroundColor: '#64748b' }]}
                  onPress={() => handleAction(actionId, 'SKIP')}
                >
                  <Text style={styles.choiceBtnText}>✕ Skip</Text>
                </TouchableOpacity>
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
    gap: 8,
  },
  choiceBtn: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 8,
  },
  choiceBtnText: {
    color: '#ffffff',
    fontWeight: 'bold',
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
});
