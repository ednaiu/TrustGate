def two_sum(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        need = target - value
        if need in seen:
            return seen[need], index
        seen[value] = index
    return None
