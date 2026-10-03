import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { NeoColors } from '../theme/neomorphism';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';

export default function StatusScreen({
  hubUrl,
  hubToken,
  connected,
  onOpenSettings,
  onRefresh,
}) {
  const [testing, setTesting] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const authHeaders = {
    'Content-Type': 'application/json',
    ...(hubToken ? { 'X-Hub-Token': hubToken, 'Authorization': `Bearer ${hubToken}` } : {}),
  };

  const handleTestNotification = async () => {
    setTesting(true);
    try {
      const res = await fetch(`${hubUrl}/api/notify`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          workflow: 'auto_job_apply',
          title: '🎯 Test Application Alert',
          message: 'Applied to Senior AI Engineer at Zomato (Score: 94%). Verified CV submitted.',
          level: 'success',
          category: 'job_applied',
          metadata: { role: 'Senior AI Engineer', company: 'Zomato' },
        }),
      });
      if (res.ok) {
        Alert.alert('Sent', 'Test alert dispatched from PC backend!');
      } else {
        Alert.alert('Error', 'Could not send test notification.');
      }
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setTesting(false);
    }
  };

  const handleTriggerActiveSlot = async () => {
    setTriggering(true);
    try {
      const res = await fetch(`${hubUrl}/api/qna/trigger`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ force: true }),
      });
      const data = await res.json();
      if (res.ok) {
        Alert.alert('Success', `Generated ${data.question_count || 0} questions for Slot ${data.slot_id}.`);
      } else {
        Alert.alert('Error', data.message || 'Trigger failed');
      }
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* PC Hub Connection Card */}
      <NeoCard>
        <View style={styles.cardHeader}>
          <Text style={styles.cardTitle}>🖥️ Computer Relay Status</Text>
          <View style={[styles.statusBadge, { backgroundColor: connected ? '#d1fae5' : '#fee2e2' }]}>
            <View style={[styles.statusDot, { backgroundColor: connected ? '#10b981' : '#ef4444' }]} />
            <Text style={[styles.statusBadgeText, { color: connected ? '#065f46' : '#991b1b' }]}>
              {connected ? 'ONLINE' : 'OFFLINE'}
            </Text>
          </View>
        </View>

        <Text style={styles.infoLabel}>Hub Address:</Text>
        <Text style={styles.infoValue}>{hubUrl}</Text>

        <Text style={styles.infoLabel}>Security Auth:</Text>
        <Text style={[styles.infoValue, { color: hubToken ? '#16a34a' : '#d97706', fontWeight: '700' }]}>
          {hubToken ? '🔒 Authenticated (X-Hub-Token set)' : '⚠️ Unauthenticated (No Token configured)'}
        </Text>

        <View style={styles.btnRow}>
          <NeoButton
            title="⚙️ Settings & Key"
            onPress={onOpenSettings}
            style={{ flex: 1, marginRight: 8 }}
          />
          <NeoButton
            title="🔄 Ping PC"
            onPress={onRefresh}
            style={{ flex: 1 }}
          />
        </View>
      </NeoCard>

      {/* Daily 3-Slot Schedule & Skip Logic Policy */}
      <NeoCard>
        <Text style={styles.cardTitle}>⏰ Daily 3-Slot Schedule Rules</Text>
        <Text style={styles.desc}>
          The multi-agent system runs at boot and executes at most 3 times a day:
        </Text>

        <View style={styles.ruleItem}>
          <Text style={styles.ruleEmoji}>🌅</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.ruleTitle}>Slot 1: Morning Fundamentals (4:00 AM – 11:00 AM)</Text>
            <Text style={styles.ruleSub}>Essential language runtimes, core lifecycle & fundamentals.</Text>
          </View>
        </View>

        <View style={styles.ruleItem}>
          <Text style={styles.ruleEmoji}>☀️</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.ruleTitle}>Slot 2: Afternoon Architecture (11:00 AM – 5:00 PM)</Text>
            <Text style={styles.ruleSub}>Scalable system design, database indexing, design patterns.</Text>
          </View>
        </View>

        <View style={styles.ruleItem}>
          <Text style={styles.ruleEmoji}>🌙</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.ruleTitle}>Slot 3: Evening Scenarios (5:00 PM – 12:00 AM)</Text>
            <Text style={styles.ruleSub}>Incident troubleshooting, STAR behavioral, edge cases.</Text>
          </View>
        </View>

        <View style={styles.skipNoteBox}>
          <Text style={styles.skipNoteTitle}>🛡️ Intelligent Skip Guarantee:</Text>
          <Text style={styles.skipNoteText}>
            If you open your PC at night, passed slots (Morning & Afternoon) are automatically SKIPPED.
            You will never receive a backlogged dump of all 3 slots simultaneously!
          </Text>
        </View>
      </NeoCard>

      {/* Multi-Agent Architecture */}
      <NeoCard>
        <Text style={styles.cardTitle}>🤖 Multi-Agent Pipeline</Text>
        <Text style={styles.desc}>
          Every question is grounded in trending/reliable GitHub repos with zero hallucinations:
        </Text>

        <View style={styles.agentList}>
          <Text style={styles.agentItem}>• <Text style={styles.bold}>JobCollectorAgent:</Text> Extracts target tech stacks from auto_job_apply database.</Text>
          <Text style={styles.agentItem}>• <Text style={styles.bold}>SourceDiscoveryAgent:</Text> Discovers vetted GitHub repos and tech handles with SafetyGuard.</Text>
          <Text style={styles.agentItem}>• <Text style={styles.bold}>QnARetrieverAgent:</Text> Fetches authentic Q&A pairs with exponential retries.</Text>
          <Text style={styles.agentItem}>• <Text style={styles.bold}>VerificationAgent:</Text> Strict source-grounding check ensuring zero agent hallucinations.</Text>
          <Text style={styles.agentItem}>• <Text style={styles.bold}>CuratorDispatchAgent:</Text> Persists to SQLite and broadcasts to mobile via WebSockets + Push.</Text>
        </View>
      </NeoCard>

      {/* Manual Actions */}
      <NeoCard>
        <Text style={styles.cardTitle}>🛠️ Diagnostics & Actions</Text>

        <View style={{ gap: 10, marginTop: 8 }}>
          <NeoButton
            title={triggering ? 'Running Multi-Agent Pipeline...' : '⚡ Trigger Active Slot Pipeline Now'}
            variant="primary"
            disabled={triggering || !connected}
            onPress={handleTriggerActiveSlot}
          />

          <NeoButton
            title={testing ? 'Sending...' : '🔔 Send Test Application Alert'}
            disabled={testing || !connected}
            onPress={handleTestNotification}
          />
        </View>
      </NeoCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: NeoColors.background,
  },
  content: {
    padding: 14,
    paddingBottom: 30,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: NeoColors.textPrimary,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 5,
  },
  statusBadgeText: {
    fontSize: 10,
    fontWeight: '800',
  },
  infoLabel: {
    fontSize: 11,
    color: NeoColors.textMuted,
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 13,
    fontWeight: '700',
    color: NeoColors.textPrimary,
    marginBottom: 12,
  },
  btnRow: {
    flexDirection: 'row',
  },
  desc: {
    fontSize: 12,
    color: NeoColors.textSecondary,
    marginBottom: 10,
    lineHeight: 17,
  },
  ruleItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  ruleEmoji: {
    fontSize: 16,
    marginRight: 8,
    marginTop: 1,
  },
  ruleTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: NeoColors.textPrimary,
  },
  ruleSub: {
    fontSize: 11,
    color: NeoColors.textMuted,
  },
  skipNoteBox: {
    marginTop: 8,
    backgroundColor: 'rgba(79, 70, 229, 0.08)',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: 'rgba(79, 70, 229, 0.2)',
  },
  skipNoteTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: '#4f46e5',
    marginBottom: 3,
  },
  skipNoteText: {
    fontSize: 11,
    color: '#334155',
    lineHeight: 16,
  },
  agentList: {
    gap: 6,
  },
  agentItem: {
    fontSize: 11,
    color: NeoColors.textSecondary,
    lineHeight: 16,
  },
  bold: {
    fontWeight: '700',
    color: NeoColors.textPrimary,
  },
});
