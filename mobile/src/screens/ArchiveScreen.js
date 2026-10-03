import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { NeoColors } from '../theme/neomorphism';
import QuestionButtonCard from '../components/QuestionButtonCard';
import PaginationControls from '../components/PaginationControls';

export default function ArchiveScreen({ hubUrl }) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('ALL');
  const [data, setData] = useState({ items: [], total: 0, total_pages: 1 });
  const [loading, setLoading] = useState(false);

  const categories = [
    'ALL',
    'Fundamentals',
    'Architecture',
    'System Design',
    'Real-World Scenarios',
    'Behavioral',
  ];

  const fetchHistory = async (targetPage = page) => {
    setLoading(true);
    try {
      let query = `${hubUrl}/api/qna/history?page=${targetPage}&page_size=8`;
      if (search.trim()) {
        query += `&search=${encodeURIComponent(search.trim())}`;
      }
      if (activeCategory !== 'ALL') {
        query += `&category=${encodeURIComponent(activeCategory)}`;
      }

      const res = await fetch(query);
      if (res.ok) {
        const json = await res.json();
        setData(json);
        setPage(targetPage);
      }
    } catch (e) {
      console.log('Error fetching history:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(1);
  }, [activeCategory, hubUrl]);

  const handleSearchSubmit = () => {
    fetchHistory(1);
  };

  const handleNextPage = () => {
    if (page < data.total_pages) {
      fetchHistory(page + 1);
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      fetchHistory(page - 1);
    }
  };

  return (
    <View style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="🔍 Search questions, answers, tech keywords..."
          placeholderTextColor="#94a3b8"
          value={search}
          onChangeText={setSearch}
          onSubmitEditing={handleSearchSubmit}
          returnKeyType="search"
        />
        {search.length > 0 ? (
          <TouchableOpacity
            onPress={() => {
              setSearch('');
              fetchHistory(1);
            }}
            style={styles.clearSearchBtn}
          >
            <Text style={styles.clearSearchText}>✕</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      {/* Category Filter Chips */}
      <View style={styles.chipsWrapper}>
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={categories}
          keyExtractor={(item) => item}
          contentContainerStyle={styles.chipsContainer}
          renderItem={({ item }) => {
            const isSelected = activeCategory === item;
            return (
              <TouchableOpacity
                onPress={() => setActiveCategory(item)}
                style={[
                  styles.filterChip,
                  isSelected && styles.filterChipActive,
                ]}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    isSelected && styles.filterChipTextActive,
                  ]}
                >
                  {item}
                </Text>
              </TouchableOpacity>
            );
          }}
        />
      </View>

      {/* Question List */}
      <FlatList
        data={data.items}
        keyExtractor={(item) => item.id}
        refreshing={loading}
        onRefresh={() => fetchHistory(page)}
        contentContainerStyle={styles.listContent}
        renderItem={({ item }) => (
          <QuestionButtonCard item={item} />
        )}
        ListFooterComponent={
          data.total_pages > 1 ? (
            <PaginationControls
              page={page}
              totalPages={data.total_pages}
              totalItems={data.total}
              onPrev={handlePrevPage}
              onNext={handleNextPage}
            />
          ) : null
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            {loading ? (
              <ActivityIndicator size="large" color="#4f46e5" />
            ) : (
              <>
                <Text style={styles.emptyIcon}>📚</Text>
                <Text style={styles.emptyTitle}>No Matching Questions</Text>
                <Text style={styles.emptyDesc}>
                  All verified interview questions generated across all past daily slots are permanently archived here.
                </Text>
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
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 6,
  },
  searchInput: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 9,
    fontSize: 13,
    color: '#1e293b',
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  clearSearchBtn: {
    marginLeft: 8,
    padding: 8,
  },
  clearSearchText: {
    fontSize: 14,
    color: '#94a3b8',
    fontWeight: 'bold',
  },
  chipsWrapper: {
    marginBottom: 6,
  },
  chipsContainer: {
    paddingHorizontal: 14,
    gap: 6,
  },
  filterChip: {
    backgroundColor: '#ebf1f8',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#cbd5e1',
  },
  filterChipActive: {
    backgroundColor: '#4f46e5',
    borderColor: '#4338ca',
  },
  filterChipText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#475569',
  },
  filterChipTextActive: {
    color: '#ffffff',
  },
  listContent: {
    padding: 14,
    paddingTop: 6,
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
