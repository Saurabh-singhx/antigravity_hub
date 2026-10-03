import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { NeoColors } from '../theme/neomorphism';
import QuestionButtonCard from '../components/QuestionButtonCard';
import SlotProgressHeader from '../components/SlotProgressHeader';
import NeoButton from '../components/NeoButton';

export default function TodayPrepScreen({
  dailyData,
  loading,
  onRefresh,
  hubUrl,
  connected,
  onTriggerSlot,
}) {
  const [triggering, setTriggering] = useState(false);

  const items = dailyData?.items || [];
  const slotProgress = dailyData?.slot_progress || {};
  const activeSlotId = dailyData?.active_slot_id;

  const handleManualTrigger = async () => {
    setTriggering(true);
    try {
      const res = await fetch(`${hubUrl}/api/qna/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true }),
      });
      const data = await res.json();
      if (res.ok) {
        Alert.alert(
          'Pipeline Executed',
          `Generated ${data.question_count || 0} questions for Slot ${data.slot_id}.`
        );
        onRefresh();
      } else {
        Alert.alert('Error', data.message || 'Could not run pipeline');
      }
    } catch (e) {
      Alert.alert('Network Error', e.message);
    } finally {
      setTriggering(false);
    }
  };

  const handleToggleMastered = async (itemId, isMastered) => {
    try {
      await fetch(`${hubUrl}/api/qna/${itemId}/mastered?mastered=${isMastered}`, {
        method: 'POST',
      });
    } catch (e) {
      console.log('Error updating mastered status:', e);
    }
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        refreshing={loading}
        onRefresh={onRefresh}
        contentContainerStyle={styles.listContent}
        ListHeaderComponent={
          <View>
            <SlotProgressHeader
              slotProgress={slotProgress}
              activeSlotId={activeSlotId}
            />

            <View style={styles.sectionHeaderRow}>
              <View>
                <Text style={styles.sectionTitle}>🎯 Today's Interview Questions</Text>
                <Text style={styles.sectionSubtitle}>
                  {items.length} questions curated for recently applied roles
                </Text>
              </View>

              <TouchableOpacity
                onPress={handleManualTrigger}
                disabled={triggering || !connected}
                style={styles.triggerBtn}
              >
                {triggering ? (
                  <ActivityIndicator size="small" color="#4f46e5" />
                ) : (
                  <Text style={styles.triggerBtnText}>⚡ Fetch Now</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        }
        renderItem={({ item }) => (
          <QuestionButtonCard
            item={item}
            onToggleMastered={handleToggleMastered}
          />
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            {loading ? (
              <ActivityIndicator size="large" color="#4f46e5" />
            ) : (
              <>
                <Text style={styles.emptyIcon}>☕</Text>
                <Text style={styles.emptyTitle}>No Questions For Today Yet</Text>
                <Text style={styles.emptyDesc}>
                  {connected
                    ? "The multi-agent workflow runs automatically when you boot your PC during active slot hours (4am-11am, 11am-5pm, 5pm-12am). Tap '⚡ Fetch Now' to trigger immediately."
                    : `Cannot reach PC Hub at ${hubUrl}. Check your Wi-Fi and PC backend status.`}
                </Text>

                {connected ? (
                  <NeoButton
                    title={triggering ? 'Running Multi-Agent Pipeline...' : '⚡ Fetch Active Slot Questions'}
                    variant="primary"
                    disabled={triggering}
                    onPress={handleManualTrigger}
                    style={{ marginTop: 14 }}
                  />
                ) : null}
              </>
            )}
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
  listContent: {
    padding: 14,
    paddingBottom: 24,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
    marginTop: 4,
    paddingHorizontal: 2,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: NeoColors.textPrimary,
  },
  sectionSubtitle: {
    fontSize: 11,
    color: NeoColors.textMuted,
    marginTop: 2,
  },
  triggerBtn: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#c7d3e3',
  },
  triggerBtnText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#4f46e5',
  },
  emptyContainer: {
    padding: 30,
    alignItems: 'center',
    marginTop: 40,
    backgroundColor: '#ebf1f8',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#d5e0ee',
  },
  emptyIcon: {
    fontSize: 34,
    marginBottom: 10,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: NeoColors.textPrimary,
    marginBottom: 6,
  },
  emptyDesc: {
    fontSize: 12,
    color: NeoColors.textSecondary,
    textAlign: 'center',
    lineHeight: 18,
  },
});
