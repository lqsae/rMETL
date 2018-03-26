
import pysam
import Queue as Q
from concensus import *
import cigar


# list_flag = {1:'I', 4:'S', 5:'H'}
list_flag = {1:'I'}
clip_flag = {4:'S', 5:'H'}
low_bandary = 20

CLIP_note = dict()
total_signal = list()
# clip_store = Q.PriorityQueue()

def revcom_complement(s): 
    basecomplement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'a': 'T', 'c': 'G', 'g': 'C', 't': 'A'} 
    letters = list(s) 
    letters = [basecomplement[base] for base in letters] 
    return ''.join(letters)[::-1]

def detect_flag(Flag):
	# Signal
	Normal_foward = 1 >> 1
	Abnormal = 1 << 2
	Reverse_complement = 1 << 4
	Supplementary_map = 1 << 11

	signal = {Abnormal: 0, Normal_foward: 1, Reverse_complement: 2, Supplementary_map:3, Reverse_complement | Supplementary_map:4}
	if Flag in signal:
		return signal[Flag]
	else:
		return 0

# def acquire_ins_part():
# 	# about insert sequence

def store_clip_pos(locus, chr, seq, flag):
	# about collecting breakpoint from clipping 
	hash_1 = int(locus /10000)
	mod = locus % 10000
	hash_2 = int(mod / 50)
	element = [locus, seq, flag]

	if hash_1 not in CLIP_note[chr]:
		CLIP_note[chr][hash_1] = dict()
		CLIP_note[chr][hash_1][hash_2] = list()
		CLIP_note[chr][hash_1][hash_2].append(element)
	else:
		if hash_2 not in CLIP_note[chr][hash_1]:
			CLIP_note[chr][hash_1][hash_2] = list()
			CLIP_note[chr][hash_1][hash_2].append(element)
		else:
			CLIP_note[chr][hash_1][hash_2].append(element)

def acquire_clip_pos(deal_cigar):
	seq = list(cigar.Cigar(deal_cigar).items())
	if seq[0][1] == 'S':
		first_pos = seq[0][0]
	else:
		first_pos = 0
	if seq[-1][1] == 'S':
		last_pos = seq[-1][0]
	else:
		last_pos = 0
	# seq = cigar.split('S')
	# if len(seq) == 3:
	# 	first_pos = int(seq[0])
	# 	last_pos = int(seq[1].split('M')[-1])
	# 	return [first_pos, last_pos]
	# if len(seq) == 1:
	# 	return []
	# if len(seq) == 2:
	# 	if seq[1] == '':
	# 		return []
	# 	first_pos = int(seq[0])
	# 	last_pos = 0
	bias = 0
	for i in seq:
		if i[1] == 'M' or i[1] == 'D':
			bias += i[0]

	return [first_pos, last_pos, bias]

def organize_split_signal(chr, primary_info, Supplementary_info, total_L):
	overlap = list()
	for i in Supplementary_info:
		seq = i.split(',')
		local_chr = seq[0]
		local_start = int(seq[1])
		local_cigar = seq[3]

		dic_starnd = {1:'+', 2: '-'}

		if dic_starnd[primary_info[4]] != seq[2]:
			continue
		if chr != local_chr:
			# return overlap
			continue
		local_set = acquire_clip_pos(local_cigar)
		# if len(local_set) == 0:
		# 	continue
		if primary_info[0] < local_start:
			if primary_info[3]+local_set[0]-total_L > 20:
				overlap.append([total_L - primary_info[3], local_set[0], primary_info[1]])
		else:
			if local_set[1]+primary_info[2]-total_L > 20:
				overlap.append([total_L - local_set[1], primary_info[2], local_start+local_set[2]-1])
			# exist some bugs

		# if local_start <= primary_end + 50 and local_start >= primary_end - 50:
		# 	local_set = acquire_clip_pos(local_cigar)
		# 	if len(local_set) != 0:
		# 		overlap.append([primary_clip, sum(local_set) - primary_clip])
	return overlap



def parse_read(read, Chr_name):
	'''
	Check:	1.Flag
			2.Supplementary mapping
			3.Seq
	'''
	local_pos = list()
	process_signal = detect_flag(read.flag) 
	if process_signal == 0:
		return local_pos
		# unmapped read

	pos_start = read.reference_start
	shift = 0
	_shift_read_ = 0
	pos_end = read.reference_end
	primary_clip_0 = 0
	primary_clip_1 = 0
	for element in read.cigar:
		if element[0] == 0 or element[0] == 2:
			shift += element[1]
		if element[0] != 2:
			_shift_read_ += element[1]
		if element[0] in list_flag and element[1] > low_bandary:
			shift += 1
			MEI_contig = read.query_sequence[_shift_read_ - element[1]:_shift_read_]
			# if process_signal == 2 or process_signal == 4:
				# MEI_contig = revcom_complement(MEI_contig)
			# if process_signal == 2 or process_signal == 4:
			# 	# strategy 1:
			# 	read_length = len(read.query_sequence)
			# 	# local_SEQ = read.query_sequence[read_length - _shift_read_:read_length - _shift_read_ + element[1]]
			# 	# MEI_contig = revcom_complement(local_SEQ)
			# 	# strategy 2:
			# 	local_SEQ = revcom_complement(read.query_sequence)
			# 	# MEI_contig = local_SEQ[_shift_read_ - element[1]:_shift_read_]
			# 	MEI_contig = local_SEQ[read_length - _shift_read_:read_length - _shift_read_ + element[1]]
			# else:
			# 	MEI_contig = read.query_sequence[_shift_read_ - element[1]:_shift_read_]
			# MEI_contig = read.query_sequence[_shift_read_-element[1]-4:_shift_read_+10]
			# judge flag !!!!!!!!
			local_pos.append([pos_start + shift, element[1], MEI_contig])

			# print read.query_name, "I", pos_start + shift
			# print MEI_contig

		if element[0] in clip_flag:

			if shift == 0:
				primary_clip_0 = element[1]
			else:
				primary_clip_1 = element[1]

			if element[1] > low_bandary:
				if shift == 0:
					clip_pos = pos_start - 1
					clip_contig = read.query_sequence[:element[1]]
					store_clip_pos(clip_pos, Chr_name, clip_contig, 0)

					# primary_clip_0 = element[1]
					# left clip size

				else:
					clip_pos = pos_start + shift - 1
					# primary_clip = read.query_length - element[1]
					clip_contig = read.query_sequence[read.query_length - element[1]:]
					store_clip_pos(clip_pos, Chr_name, clip_contig, 1)

					# primary_clip_1 = read.query_length - element[1]
					# right clip size


				# store_clip_pos(clip_pos, Chr_name, clip_contig)
				# print read.query_name, "S"
				# print clip_contig
				# hash_1 = int(clip_pos / 10000)
				# mod_1 = int(clip_pos % 10000)
				# hash_2 = int(mod_1 / 50)
				# if hash_1 not in CLIP_note[Chr_name]:
				# 	CLIP_note[Chr_name][hash_1] = dict()
				# 	CLIP_note[Chr_name][hash_1][hash_2] = list()
				# 	CLIP_note[Chr_name][hash_1][hash_2].append(clip_pos)
				# else:
				# 	if hash_2 not in CLIP_note[Chr_name][hash_1]:
				# 		CLIP_note[Chr_name][hash_1][hash_2]
				# # if clip_pos not in CLIP_note[Chr_name]:
				# # 	CLIP_note[Chr_name][clip_pos] = 1
				# # else:
				# # 	CLIP_note[Chr_name][clip_pos] += 1
				# CLIP_note[Chr_name].put(clip_pos)
				# print Chr_name, clip_pos
	# cluster_pos = sorted(cluster_pos, key = lambda x:x[0])
			# return [r_start + shift, element[1]]

	if process_signal == 1 or process_signal == 2:
		Tags = read.get_tags()
		chr = Chr_name
		# primary_clip = pos_start
		primary_info = [pos_start, pos_end, primary_clip_0, primary_clip_1, process_signal]

		for i in Tags:
			if i[0] == 'SA':
				Supplementary_info = i[1].split(';')[:-1]
				# print process_signal
				# print chr, primary_info, read.query_length
				# print read.cigar
				# print i[1].split(';')[-1]
				overlap = organize_split_signal(chr, primary_info, Supplementary_info, read.query_length)
				for k in overlap:
					# print k
					MEI_contig = read.query_sequence[k[0]:k[1]]
					local_pos.append([k[2], k[1] - k[0], MEI_contig])

	return local_pos

def merge_siganl(chr, cluster):
	# for i in cluster:
	# 	if i[2] >= 5:
	# 		total_signal.append("%s\t%d\t%d\t%d\t%s\n"%(chr, i[0], i[1], i[2], i[3]))
	# 		# print("%s\t%d\t%d\t%d"%(chr, i[0], i[1], i[2]))
	for i in cluster:
		for j in i:
			total_signal.append(j)

def acquire_clip_locus(down, up, chr):
	list_clip = list()
	if int(up/10000) == int(down/10000):
		key_1 = int(down/10000)
		if key_1 not in CLIP_note[chr]:
			return list_clip
		for i in xrange(int((up%10000)/50)-int((down%10000)/50)+1):
			# exist a bug ***********************************
			key_2 = int((down%10000)/50)+i
			if key_2 not in CLIP_note[chr][key_1]:
				continue
			for ele in CLIP_note[chr][key_1][key_2]:
				if ele[0] >= down and ele[0] <= up:
					list_clip.append(ele)
	else:
		key_1 = int(down/10000)
		if key_1 in CLIP_note[chr]:
			for i in xrange(200-int((down%10000)/50)):
				# exist a bug ***********************************
				key_2 = int((down%10000)/50)+i
				if key_2 not in CLIP_note[chr][key_1]:
					continue
				for ele in CLIP_note[chr][key_1][key_2]:
					if ele[0] >= down and ele[0] <= up:
						list_clip.append(ele)
		key_1 += 1
		if key_1 not in CLIP_note[chr]:
			return list_clip
		for i in xrange(int((up%10000)/50)+1):
			# exist a bug ***********************************
			key_2 = i
			if key_2 not in CLIP_note[chr][key_1]:
				continue
			for ele in CLIP_note[chr][key_1][key_2]:
				if ele[0] >= down and ele[0] <= up:
					list_clip.append(ele)
	return list_clip

def merge_pos(pos_list, chr):
	start = list()
	end = list()
	for ele in pos_list:
		start.append(ele[0])
		end.append(ele[0] + ele[1])

	search_down = min(start) - 10
	search_up = max(start) + 10
	temp_clip = acquire_clip_locus(search_down, search_up, chr)

	# concensus, ref_pos = construct_concensus_seq(pos_list, temp_clip)
	result = construct_concensus_info(pos_list, temp_clip)
	if result != 0:
		for i in xrange(len(result)):
			result[i] = ">" + chr + result[i]
		return result
	else:
		return 0

	# print ref_pos
	# print concensus

	'''
	TE detect
	'''

	# total_breakpoint = int((sum(start) + sum(temp_clip)) / (len(pos_list) + len(temp_clip)))
	# total_length = int(sum(end)/len(pos_list)) - total_breakpoint
	# total_read_count = len(pos_list) + len(temp_clip)
	# return	[ref_pos, len(concensus), total_read_count, concensus]
	# return [int(sum(start)/len(pos_list)), int(sum(end)/len(pos_list)) - int(sum(start)/len(pos_list)), len(pos_list)]

def cluster(pos_list, chr):
	_cluster_ = list()
	temp = list()
	temp.append(pos_list[0])
	for pos in pos_list[1:]:
		# if temp[-1][0] + temp[-1][1] < pos[0]:
		if temp[-1][0] + 20 < pos[0]:
			result = merge_pos(temp, chr)
			if result != 0:
				_cluster_.append(result)
			temp = list()
			temp.append(pos)
		else:
			temp.append(pos)
	result = merge_pos(temp, chr)
	if result != 0:
		_cluster_.append(result)
	# _cluster_.append(merge_pos(temp, chr))
	return _cluster_

def load_sam(p1, p2):
	'''
	Load_BAM_File
	library:	pysam.AlignmentFile
	'''
	samfile = pysam.AlignmentFile(p1)
	# print(samfile.get_index_statistics())
	contig_num = len(samfile.get_index_statistics())
	print("[INFO]: The total number of chromsomes: %d"%(contig_num))
	# Acquire_Chr_name
	for _num_ in xrange(contig_num):
		Chr_name = samfile.get_reference_name(_num_)
		print("[INFO]: Resolving the chromsome %s."%(Chr_name))
		# Chr_length = samfile.lengths[_num_]
		if Chr_name not in CLIP_note:
			# CLIP_note[Chr_name] = [0] * Chr_length
			# CLIP_note[Chr_name] = Q.PriorityQueue()
			CLIP_note[Chr_name] = dict()

		cluster_pos = list()
		for read in samfile.fetch(Chr_name):
			feed_back = parse_read(read, Chr_name)

			if len(feed_back) > 0:
				for i in feed_back:
					cluster_pos.append(i)
		# while not CLIP_note[Chr_name].empty():
		# 	print Chr_name, CLIP_note[Chr_name].get()
		# print CLIP_note[Chr_name][6]
		cluster_pos = sorted(cluster_pos, key = lambda x:x[0])
		if len(cluster_pos) == 0:
			Cluster = list()
		else:
			Cluster = cluster(cluster_pos, Chr_name)
		print("[INFO]: %d Alu signal locuses in the chromsome %s."%(len(Cluster), Chr_name))
		# merge_siganl(Chr_name, Cluster)
		# break
		out_signal = open(p2, 'a+')
		for i in Cluster:
			for j in i:
				out_signal.write(j)
		out_signal.close()

	# out_signal = open(p2, 'w')
	# for i in total_signal:
	# 	out_signal.write(i)
	# out_signal.close()
	samfile.close()