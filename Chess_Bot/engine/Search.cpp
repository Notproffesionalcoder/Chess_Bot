#include "Search.h"

bool break_now = false;

state curr_state;

Value search(Depth depth, Value alpha, Value beta)
{
	nodes++;

	// printf("search(%d, %d, %d)\n", depth, alpha, beta);
	// curr_state.print();

	Bitstring curr_board_hash = curr_state.get_hash();
	Bitstring key = curr_board_hash % TABLE_SIZE;

	if (tt_exists[key] && tt_depths[key] >= depth && tt_hashes[key] == curr_board_hash)
	{
		// printf("tt hit, %d\n", tt_evals[key]);
		tb_hits++;
		return tt_evals[key];
	}

	if (curr_state.adjucation()) {
		// printf("adjucation\n");
		return DRAWN;
	}


	if (curr_state.king_attacked()) {
		// printf("king attacked\n");
		return MATE;
	}

	if (break_now) {
		return eval(curr_state);
	}

	if (depth <= DEPTH_ZERO) {
		return qsearch(alpha, beta, depth);
	}

	Value curr_eval;
	if (tt_exists[key] && tt_hashes[key] == curr_board_hash) {
		// tt entry can be used as more accurate static eval
		curr_eval = tt_evals[key];
	} else {
		curr_eval = eval(curr_state);
	}

	// Futility pruning
	// TODO: implement improving
	if (depth < 7 && (curr_eval - futility_margin(depth, false) >= beta))
	{
		// printf("futility prune: %d\n", curr_eval);
		return curr_eval;
	}

	// Razor pruning and extended razor pruning
	if (depth < 1) {
		if (curr_eval + RAZOR_MARGIN < alpha) {
			// printf("razor prune\n");
			return qsearch(alpha, beta, DEPTH_ZERO);
		}
	} 

	std::vector<int> moves = curr_state.list_moves();
	eval_cache.clear();

	bool mate = true;
	for (int i : moves)
	{
		curr_state.make_move(i);

		if (curr_state.king_attacked()) {
			eval_cache[i] = MATED;
		} else {
			mate = false;

			Bitstring hash = curr_state.get_hash();
			if (tt_exists[hash % TABLE_SIZE] && tt_hashes[hash % TABLE_SIZE] == hash) {
				eval_cache[i] = -tt_evals[hash % TABLE_SIZE];
			}
			else {
				eval_cache[i] = -eval(curr_state);
			}
		}

		curr_state.unmake_move(i);
	}
	if (mate)
	{
		if (curr_state.is_check()) {
			// printf("checkmate\n");
			return MATED;
		}
		else {
			// printf("stalemate\n");
			return DRAWN;
		}
	}
	
	std::sort(moves.begin(), moves.end(), move_comparator);
	Value value = -VALUE_INFINITE;

	for (int move : moves)
	{
		// printf("Considering %s\n", curr_state.move_to_string(move).c_str());

		curr_state.make_move(move);
		Value x = -search(depth - ONE_PLY, -beta, -alpha);
		curr_state.unmake_move(move);

		value = std::max(value, x);
		alpha = std::max(alpha, value);

		if (alpha >= beta) {
			// printf("alpha beta cutoff: %d\n", alpha);
			return alpha;
		}
	}

	tt_exists[key] = true;
	tt_depths[key] = depth;
	tt_evals[key] = value;
	tt_hashes[key] = curr_board_hash;

	// printf("done searching, returned %d\n", value);
	// curr_state.print();

	return value;
}

// Only searches captures and queen promotions to avoid horizon effect
Value qsearch(Value alpha, Value beta, Depth depth)
{
	qsearch_nodes++;

	depth_qsearched = std::min(depth_qsearched, depth);
	
	// printf("qsearch(%d, %d)\n", alpha, beta);
	// curr_state.print();

	Bitstring curr_board_hash = curr_state.get_hash();
	Bitstring key = curr_board_hash % TABLE_SIZE;

	if (tt_exists[key] && tt_depths[key] >= DEPTH_QS_NO_CHECKS && tt_hashes[key] == curr_board_hash)
	{
		// printf("tt hit: %d\n", tt_evals[key]);
		qsearch_hits++;
		return tt_evals[key];
	}

	if (curr_state.adjucation()) {
		// printf("adjucation\n");
		return DRAWN;
	}

	if (curr_state.king_attacked()){
		// printf("king attacked\n");
		return MATE;
	}
	
	Value curr_eval;
	if (tt_exists[key] && tt_hashes[key] == curr_board_hash) {
		// tt entry can be used as more accurate static eval
		curr_eval = tt_evals[key];
	} else {
		curr_eval = eval(curr_state);
	}

	if (depth < QS_MIN_DEPTH) {
		return curr_eval;
	}

	// Futility pruning
	if (depth - QS_MIN_DEPTH < 5 && (curr_eval - futility_margin(depth - QS_MIN_DEPTH, false) >= beta))
	{
		// printf("futility prune: %d\n", curr_eval);
		return curr_eval;
	}

	std::vector<int> ordered_moves;

	eval_cache.clear();

	bool mate = true;
	for (int i : curr_state.list_moves())
	{
		curr_state.make_move(i);
		if (mate && !curr_state.king_attacked())
		{
			mate = false;
		}

		if ((((i >> 15) & 7) != 0) || ((((i >> 18) & 3) == 2) && (((i >> 20) & 3) == 3)))
		{
			ordered_moves.push_back(i);
			
			Bitstring hash = curr_state.get_hash();
			if (tt_exists[hash % TABLE_SIZE] && tt_hashes[hash % TABLE_SIZE] == hash) {
				// printf("using tt for eval of move %s\n", curr_state.move_to_string(i).c_str());
				eval_cache[i] = -tt_evals[hash % TABLE_SIZE];
			}
			else {
				eval_cache[i] = -eval(curr_state);
			}
		}

		curr_state.unmake_move(i);
	}
	if (mate)
	{
		if (curr_state.is_check()) {
			// printf("checkmate\n");
			return MATED;
		}
		else {
			// printf("stalemate\n");
			return DRAWN;
		}
	}

	if (break_now || ordered_moves.size() == 0)
	{
		// printf("no moves: %d\n", curr_eval);
		return curr_eval;
	}

	if (curr_eval >= beta)
	{ // Standing pat
		// printf("stand-pat: %d\n", curr_eval);
		return curr_eval;
	}

	// printf("static eval = %d\n", curr_eval);

	Value value = curr_eval;
	alpha = std::max(alpha, value);

	std::sort(ordered_moves.begin(), ordered_moves.end(), move_comparator);

	for (int move : ordered_moves)
	{
		// printf("Considering %s\n", curr_state.move_to_string(move).c_str());

		curr_state.make_move(move);
		Value x = -qsearch(-beta, -alpha, depth - ONE_PLY);
		curr_state.unmake_move(move);

		value = std::max(value, x);
		alpha = std::max(alpha, value);

		if (alpha >= beta) {
			// printf("alpha beta cutoff: %d\n", alpha);
			return alpha;
		}
	}

	tt_exists[key] = true;
	tt_depths[key] = DEPTH_QS_NO_CHECKS;
	tt_evals[key] = value;
	tt_hashes[key] = curr_board_hash;
	
	// printf("done qsearching, returned %d\n", value);
	// curr_state.print();

	return value;
}